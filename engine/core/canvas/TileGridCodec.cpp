#include "TileGridCodec.hpp"
#include "CanvasLimits.hpp"
#include "../../infrastructure/compression/Lz4Codec.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <utility>

namespace aladyn::engine::canvas::TileGridCodec {

namespace {

constexpr char kMagic[4] = {'L', 'M', 'N', 'T'};
constexpr uint8_t kCodecRaw = 0;
constexpr uint8_t kCodecLz4 = 1;

void putU16(std::vector<uint8_t>& out, uint16_t value) {
    out.push_back(static_cast<uint8_t>(value & 0xFF));
    out.push_back(static_cast<uint8_t>(value >> 8));
}

void putU32(std::vector<uint8_t>& out, uint32_t value) {
    for (int shift = 0; shift < 32; shift += 8) out.push_back(static_cast<uint8_t>((value >> shift) & 0xFF));
}

uint16_t getU16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }

uint32_t getU32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

// Um tile sem nenhum pixel visível não é dado: os pixels de alfa 0 não carregam cor.
bool hasVisiblePixel(const PixelBuffer& buffer) noexcept {
    const uint8_t* data = buffer.getData();
    const size_t size = buffer.getSizeInBytes();
    for (size_t i = 3; i < size; i += 4) {
        if (data[i] != 0) return true;
    }
    return false;
}

struct EntryView {
    uint16_t tx{0};
    uint16_t ty{0};
    uint8_t codec{0};
    const uint8_t* data{nullptr};
    size_t size{0};
};

[[noreturn]] void bad(const char* what) { throw std::invalid_argument(std::string("layer tile data: ") + what); }

} // namespace

std::vector<uint8_t> encode(const TileGrid& grid) {
    struct Source { int tx; int ty; const Tile* tile; };
    std::vector<Source> sources;
    sources.reserve(grid.getActiveTilesCount());
    grid.forEachTile([&](const TileIndex& index, const Tile& tile) {
        if (hasVisiblePixel(tile.getBuffer())) sources.push_back({index.x, index.y, &tile});
    });
    std::sort(sources.begin(), sources.end(), [](const Source& a, const Source& b) {
        return a.ty != b.ty ? a.ty < b.ty : a.tx < b.tx;
    });

    std::vector<uint8_t> out;
    out.reserve(kHeaderBytes + sources.size() * (kEntryHeaderBytes + Tile::TILE_BYTES / 2));
    out.insert(out.end(), kMagic, kMagic + 4);
    putU16(out, kFormat);
    putU16(out, static_cast<uint16_t>(Tile::TILE_SIZE));
    putU32(out, static_cast<uint32_t>(grid.getWidth()));
    putU32(out, static_cast<uint32_t>(grid.getHeight()));
    putU32(out, static_cast<uint32_t>(sources.size()));
    putU32(out, 0);

    std::vector<uint8_t> packed(compression::Lz4Codec::maxCompressedSize(Tile::TILE_BYTES));
    for (const Source& source : sources) {
        const PixelBuffer& buffer = source.tile->getBuffer();
        size_t stored = compression::Lz4Codec::compressBlock(buffer.getData(), Tile::TILE_BYTES, packed.data(), packed.size());
        const bool useLz4 = stored != 0 && stored < Tile::TILE_BYTES;
        const uint8_t* payload = useLz4 ? packed.data() : buffer.getData();
        if (!useLz4) stored = Tile::TILE_BYTES;

        putU16(out, static_cast<uint16_t>(source.tx));
        putU16(out, static_cast<uint16_t>(source.ty));
        out.push_back(useLz4 ? kCodecLz4 : kCodecRaw);
        out.insert(out.end(), 3, 0);
        putU32(out, static_cast<uint32_t>(stored));
        out.insert(out.end(), payload, payload + stored);
    }
    return out;
}

void decode(const uint8_t* data, size_t size, TileGrid& grid) {
    if (!data || size < kHeaderBytes) bad("shorter than its header");
    if (std::memcmp(data, kMagic, 4) != 0) bad("not a layer tile block");
    if (getU16(data + 4) != kFormat) bad("unknown format version");
    if (getU16(data + 6) != Tile::TILE_SIZE) bad("tile size does not match this engine");
    const uint32_t width = getU32(data + 8);
    const uint32_t height = getU32(data + 12);
    const uint32_t count = getU32(data + 16);
    if (getU32(data + 20) != 0) bad("reserved field is not zero");
    if (width < 1 || height < 1 || width > static_cast<uint32_t>(kMaxCanvasDimension) ||
        height > static_cast<uint32_t>(kMaxCanvasDimension)) {
        bad("canvas size out of range");
    }
    if (static_cast<int>(width) != grid.getWidth() || static_cast<int>(height) != grid.getHeight()) {
        bad("canvas size differs from the layer it is restored into");
    }
    const uint64_t capacity = static_cast<uint64_t>(grid.getTilesCountX()) * static_cast<uint64_t>(grid.getTilesCountY());
    if (count > capacity) bad("more tiles than the canvas holds");

    // First pass: the structure, without touching the grid or decoding anything.
    std::vector<EntryView> entries;
    entries.reserve(count);
    size_t offset = kHeaderBytes;
    int64_t previous = -1;
    for (uint32_t i = 0; i < count; ++i) {
        if (size - offset < kEntryHeaderBytes) bad("truncated tile record");
        const uint8_t* head = data + offset;
        EntryView entry;
        entry.tx = getU16(head);
        entry.ty = getU16(head + 2);
        entry.codec = head[4];
        if (head[5] != 0 || head[6] != 0 || head[7] != 0) bad("reserved field is not zero");
        entry.size = getU32(head + 8);
        offset += kEntryHeaderBytes;
        if (entry.tx >= grid.getTilesCountX() || entry.ty >= grid.getTilesCountY()) bad("tile outside the canvas");
        const int64_t key = static_cast<int64_t>(entry.ty) * grid.getTilesCountX() + entry.tx;
        if (key <= previous) bad("tiles out of order or repeated");
        previous = key;
        if (entry.codec == kCodecRaw) {
            if (entry.size != Tile::TILE_BYTES) bad("raw tile has the wrong size");
        } else if (entry.codec == kCodecLz4) {
            if (entry.size == 0 || entry.size > compression::Lz4Codec::maxCompressedSize(Tile::TILE_BYTES)) {
                bad("compressed tile has an impossible size");
            }
        } else {
            bad("unknown tile codec");
        }
        if (size - offset < entry.size) bad("truncated tile data");
        entry.data = data + offset;
        offset += entry.size;
        entries.push_back(entry);
    }
    if (offset != size) bad("bytes after the last tile");

    // Second pass: decode every tile into a buffer of its own, in parallel (each one is a
    // separate 64 KB block: opening a dense 4K document is ten layers of 510 tiles), then put
    // them in a grid of its own and replace the layer only when all of it decoded.
    std::vector<std::shared_ptr<PixelBuffer>> buffers(entries.size());
    std::vector<char> decodedOk(entries.size(), 0);
    const int total = static_cast<int>(entries.size());
    #pragma omp parallel for schedule(static) if(total >= 16)
    for (int i = 0; i < total; ++i) {
        const EntryView& entry = entries[static_cast<size_t>(i)];
        auto buffer = std::make_shared<PixelBuffer>(Tile::TILE_SIZE, Tile::TILE_SIZE, utils::ColorRGBA{0, 0, 0, 0});
        bool ok = true;
        if (entry.codec == kCodecRaw) {
            std::memcpy(buffer->getData(), entry.data, Tile::TILE_BYTES);
        } else {
            ok = compression::Lz4Codec::decompressBlock(entry.data, entry.size, buffer->getData(), Tile::TILE_BYTES);
        }
        buffers[static_cast<size_t>(i)] = std::move(buffer);
        decodedOk[static_cast<size_t>(i)] = ok ? 1 : 0;
    }
    if (std::find(decodedOk.begin(), decodedOk.end(), 0) != decodedOk.end()) bad("compressed tile is corrupt");

    TileGrid decoded(grid.getWidth(), grid.getHeight());
    for (size_t i = 0; i < entries.size(); ++i) {
        if (!decoded.adoptTile(entries[i].tx, entries[i].ty, std::move(buffers[i]))) bad("tile could not be created");
    }
    grid = std::move(decoded);
}

} // namespace aladyn::engine::canvas::TileGridCodec
