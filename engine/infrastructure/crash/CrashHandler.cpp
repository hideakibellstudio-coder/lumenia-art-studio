#include "CrashHandler.hpp"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <dbghelp.h>
#include <cwchar>
#ifdef _MSC_VER
#pragma comment(lib, "dbghelp.lib")
#endif
#endif

namespace aladyn::engine::crash {

#ifdef _WIN32
namespace {

// Filled once at install: the exception filter must not allocate.
constexpr size_t kPathCapacity = 1024;
wchar_t g_directory[kPathCapacity] = {};

bool widen(const std::string& utf8, wchar_t* out, size_t capacity) {
    if (utf8.empty()) return false;
    const int needed = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8.data(),
                                           static_cast<int>(utf8.size()), nullptr, 0);
    if (needed <= 0 || static_cast<size_t>(needed) >= capacity) return false;
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, utf8.data(), static_cast<int>(utf8.size()), out, needed);
    out[needed] = L'\0';
    return true;
}

bool writeDump(const wchar_t* path, EXCEPTION_POINTERS* exception) {
    HANDLE file = CreateFileW(path, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    MINIDUMP_EXCEPTION_INFORMATION info{};
    info.ThreadId = GetCurrentThreadId();
    info.ExceptionPointers = exception;
    info.ClientPointers = FALSE;
    // Stacks, thread state and the memory the stacks point to: enough to read the
    // failing frame without dumping the canvas tiles (gigabytes on a large document).
    const auto type = static_cast<MINIDUMP_TYPE>(MiniDumpWithIndirectlyReferencedMemory |
                                                 MiniDumpWithThreadInfo | MiniDumpScanMemory);
    const BOOL written = MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), file, type,
                                           exception ? &info : nullptr, nullptr, nullptr);
    CloseHandle(file);
    return written == TRUE;
}

LONG WINAPI onUnhandledException(EXCEPTION_POINTERS* exception) {
    SYSTEMTIME now;
    GetLocalTime(&now);
    wchar_t path[kPathCapacity + 64];
    std::swprintf(path, sizeof(path) / sizeof(path[0]), L"%ls\\lumenia-%04u%02u%02u-%02u%02u%02u-%lu.dmp",
                  g_directory, static_cast<unsigned>(now.wYear), static_cast<unsigned>(now.wMonth),
                  static_cast<unsigned>(now.wDay), static_cast<unsigned>(now.wHour),
                  static_cast<unsigned>(now.wMinute), static_cast<unsigned>(now.wSecond),
                  static_cast<unsigned long>(GetCurrentProcessId()));
    writeDump(path, exception);
    return EXCEPTION_CONTINUE_SEARCH;
}

} // namespace

bool installCrashHandler(const std::string& directoryUtf8) {
    wchar_t directory[kPathCapacity] = {};
    if (!widen(directoryUtf8, directory, kPathCapacity)) return false;
    const DWORD attributes = GetFileAttributesW(directory);
    if (attributes == INVALID_FILE_ATTRIBUTES || !(attributes & FILE_ATTRIBUTE_DIRECTORY)) return false;
    std::wmemcpy(g_directory, directory, kPathCapacity);
    SetUnhandledExceptionFilter(onUnhandledException);
    return true;
}

bool writeDiagnosticDump(const std::string& fileUtf8) {
    wchar_t path[kPathCapacity] = {};
    if (!widen(fileUtf8, path, kPathCapacity)) return false;
    return writeDump(path, nullptr);
}

#else

bool installCrashHandler(const std::string&) { return false; }

bool writeDiagnosticDump(const std::string&) { return false; }

#endif

} // namespace aladyn::engine::crash
