# 🎨 Lumenia Art Studio — User Guide

Welcome to **Lumenia Art Studio**, a professional digital painting and 2D concept art workstation engineered for high fidelity and ultra-low stroke latency, powered by the native **ALADYN C++20** engine.

---

## ⚡ 1. System Overview

Lumenia is designed under the **ARCcC** (*Atomic Recursive Componentization by Contract*) architecture, strictly separating the visual interface (PySide6) from the physical engine (C++20 with SIMD AVX2 acceleration).

- **Infinite Resolution with Sparse Tiles (64×64)**: The canvas manages sparse memory blocks, allocating memory only where paint strokes exist.
- **Catmull-Rom & Clark Interpolation**: Ultra-smooth stylus response eliminating dotted gaps even during high-velocity motions.
- **Multi-Document Interface (MDI)**: Seamlessly work on multiple documents concurrently with isolated native engine instances.

---

## 🖌️ 2. Painting Tools

| Shortcut | Tool | Description |
| :---: | :--- | :--- |
| **B** | **Brush** | Primary stroke tool with modular physics (Oil, Watercolor, Graphite, Ink). |
| **E** | **Eraser** | Erases pigment while preserving alpha channels with configurable smoothing. |
| **U** | **Vector Shapes** | Rectangles, ellipses, regular polygons, and stars with stroke or fill. |
| **T** | **Text** | In-canvas typographic engine with live font styling on rasterized layers. |
| **I** | **Eyedropper** | 1×1 single pixel or 3×3 / 5×5 area-averaged color sampling. |
| **G** | **Paint Bucket** | Contiguous or global flood-fill with smart tolerance and anti-aliasing. |
| **W** | **Magic Wand** | Color-similarity selection with expandable tolerances. |
| **Ctrl+T** | **Transform** | Free transform with movable pivot, 8 handles, and bicubic resample. |

---

## 📐 3. Perspective Guides & Symmetry

Open the **Geometry & Symmetry** sidebar to activate interactive guides:
- **Planar Rulers**: Straight lines, Bézier curves, and isometric grids.
- **Perspective**: 1-Point (Central), 2-Point (Architecture), and 3-Point (Aerial/Zenith).
- **Curvilinear 6-Point Perspective**: Real-time 360° spherical fisheye projection grid.
- **Symmetry Studio**: Free Mirror, Vertical Mirror, Horizontal Mirror, Double Mirror, Radial (3 to 36 axes), and Kaleidoscope.

---

## 🎭 4. Layers & Blending Modes

- **Hierarchical Organization**: Create nested layer groups with instantaneous fold/unfold.
- **Supported Blending Modes**:
  - *Normal*, *Multiply*, *Screen*, *Overlay*, *Soft Light*, *Hard Light*.
  - *Darken*, *Lighten*, *Linear Dodge (Additive)*, *Erase*.
- **Advanced Features**: Clipping Masks, Alpha Lock, and Non-Destructive Adjustment Layers.

---

## 🎨 5. Color Modes & Soft Proofing

Via the **View > Color Proofing & Rendering** menu:
- **Gamut Simulation**: Live preview of your artwork in CMYK spaces (FOGRA39, US Web Coated) and target displays.
- **Visual Accessibility**: Built-in colorblindness simulation (Protanopia, Deuteranopia, Tritanopia, and Achromatopsia).
- **Deep Color Pipeline (RGBA16F)**: 64-bit per pixel half-float color processing with linear gamma blending.

---

## ⌨️ 6. Essential Shortcuts

- `Ctrl + N`: New Document
- `Ctrl + O`: Open File
- `Ctrl + S`: Save Document
- `Ctrl + Shift + S`: Save As
- `Ctrl + Z` / `Ctrl + Y`: Undo / Redo
- `Ctrl + =` / `Ctrl + -`: Zoom In / Zoom Out
- `Space + Drag`: Pan Canvas
- `Ctrl + A` / `Ctrl + D`: Select All / Deselect
