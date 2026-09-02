# 🎨 Lumenia Art Studio — Guía de Usuario

Bienvenido a **Lumenia Art Studio**, una estación de trabajo profesional para pintura digital y arte conceptual 2D con alta fidelidad y latencia ultra-baja, impulsada por el motor nativo **ALADYN C++20**.

---

## ⚡ 1. Visión General del Sistema

Lumenia ha sido diseñado bajo la arquitectura **ARCcC** (*Atomic Recursive Componentization by Contract*), separando estrictamente la interfaz visual (PySide6) del motor físico de alto rendimiento (C++20 con aceleración SIMD AVX2).

- **Resolución Infinita con Tiles Dispersos (64×64)**: El lienzo gestiona bloques dispersos de memoria, asignando espacio únicamente donde existen trazos de pintura.
- **Interpolación Catmull-Rom & Clark**: Respuesta suave del lápiz óptico, eliminando cortes punteados incluso en movimientos de alta velocidad.
- **Interfaz Multidocumento (MDI)**: Trabaje en múltiples documentos simultáneamente con instancias aisladas del motor nativo.

---

## 🖌️ 2. Herramientas de Pintura

| Atajo | Herramienta | Descripción |
| :---: | :--- | :--- |
| **B** | **Pincel** | Herramienta principal con física modular (Óleo, Acuarela, Grafito, Tinta). |
| **E** | **Borrador** | Elimina pigmentos preservando canales alfa con suavizado configurable. |
| **U** | **Formas Vectoriales** | Rectángulos, elipses, polígonos regulares y estrellas con trazo o relleno. |
| **T** | **Texto** | Inserción tipográfica sobre el lienzo con estilo en capas rasterizadas. |
| **I** | **Cuentagotas** | Muestreo de color de 1×1 píxel o promedio de área (3×3, 5×5). |
| **G** | **Bote de Pintura** | Relleno contiguo o global con tolerancia inteligente y anti-alias. |
| **W** | **Varita Mágica** | Selección por similitud cromática con tolerancia ajustable. |
| **Ctrl+T** | **Transformación** | Transformación libre con pivote móvil, 8 manipuladores y remuestreo bicúbico. |

---

## 📐 3. Guías de Perspectiva y Simetría

Abra el panel lateral de **Geometría y Simetría** para activar reglas interactivas:
- **Reglas Planas**: Líneas rectas, curvas Bézier y cuadrículas isométricas.
- **Perspectiva**: 1 Punto (Central), 2 Puntos (Arquitectura) y 3 Puntos (Aérea/Cenital).
- **Perspectiva Curvilínea 6P**: Proyección ojo de pez esférica de 360° en tiempo real.
- **Estudio de Simetría**: Espejo Libre, Espejo Vertical, Espejo Horizontal, Espejo Doble, Radial (3 a 36 ejes) y Caleidoscopio.

---

## 🎭 4. Capas y Modos de Fusión

- **Organización Jerárquica**: Cree grupos de capas anidados con colapso y despliegue instantáneos.
- **Modos de Fusión Soportados**:
  - *Normal*, *Multiplicar*, *Trama (Screen)*, *Superponer (Overlay)*, *Luz Suave*, *Luz Fuerte*.
  - *Oscurecer*, *Aclarar*, *Sobreexposición Lineal (Añadir)*, *Borrar*.
- **Funciones Avanzadas**: Máscaras de Recorte, Bloqueo Alfa y Capas de Ajuste No-Destructivas.

---

## 🎨 5. Modos de Color y Prueba de Color (Soft Proofing)

A través del menú **Ver > Prueba de Color y Renderizado**:
- **Simulación de Gama**: Vista previa en tiempo real de su obra en espacios de color CMYK (FOGRA39, US Web Coated) y pantallas objetivo.
- **Accesibilidad Visual**: Simulación integrada de daltonismo (Protanopia, Deuteranopia, Tritanopia y Acromatopsia).
- **Pipeline Deep Color (RGBA16F)**: Procesamiento de color de 64 bits por píxel con mezcla gamma lineal.

---

## ⌨️ 6. Atajos Esenciales

- `Ctrl + N`: Nuevo Documento
- `Ctrl + O`: Abrir Archivo
- `Ctrl + S`: Guardar Documento
- `Ctrl + Shift + S`: Guardar Como
- `Ctrl + Z` / `Ctrl + Y`: Deshacer / Rehacer
- `Ctrl + =` / `Ctrl + -`: Acercar / Alejar Zoom
- `Espacio + Arrastre`: Desplazar Lienzo (Pan)
- `Ctrl + A` / `Ctrl + D`: Seleccionar Todo / Deseleccionar
