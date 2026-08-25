"""In-place Text Overlay Editor Widget for Canvas."""

from PySide6 import QtWidgets, QtCore, QtGui

class TextOverlayEditor(QtWidgets.QFrame):
    """Widget de edição de texto in-place sobreposto diretamente no canvas com tipografia em tempo real."""

    def __init__(self, parent, canvas_x: float, canvas_y: float, settings: dict):
        super().__init__(parent)
        self.canvas_widget = parent
        self.canvas_pos = QtCore.QPointF(canvas_x, canvas_y)
        self.settings = dict(settings)

        self.setObjectName("TextOverlayFrame")
        self.setStyleSheet("""
            #TextOverlayFrame {
                background: rgba(26, 26, 36, 0.94);
                border: 1.5px dashed #9333ea;
                border-radius: 6px;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.text_edit = QtWidgets.QTextEdit(self)
        self.text_edit.setPlaceholderText("Digite seu texto aqui...")
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                padding: 2px;
            }
        """)

        layout.addWidget(self.text_edit)
        self.apply_typography(self.settings)

        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.installEventFilter(self)

        self.update_screen_position()
        self.show()
        self.raise_()
        self.text_edit.setFocus()

    def apply_typography(self, settings: dict):
        self.settings.update(settings)
        font_family = self.settings.get("font_family", "Segoe UI")
        font_size_pt = max(6, int(self.settings.get("font_size", 36)))
        bold = bool(self.settings.get("bold", False))
        italic = bool(self.settings.get("italic", False))
        underline = bool(self.settings.get("underline", False))
        align = self.settings.get("align", "left")
        col = QtGui.QColor(self.settings.get("color", QtGui.QColor(255, 255, 255, 255)))

        zoom = max(0.01, getattr(self.canvas_widget, "zoom", 1.0))
        screen_font_size = max(8.0, font_size_pt * zoom)

        qfont = QtGui.QFont(font_family)
        qfont.setPointSizeF(screen_font_size)
        qfont.setBold(bold)
        qfont.setItalic(italic)
        qfont.setUnderline(underline)

        self.text_edit.setFont(qfont)

        if align == "center":
            self.text_edit.setAlignment(QtCore.Qt.AlignHCenter)
        elif align == "right":
            self.text_edit.setAlignment(QtCore.Qt.AlignRight)
        else:
            self.text_edit.setAlignment(QtCore.Qt.AlignLeft)

        self.text_edit.setTextColor(col)
        self._adjust_size()

    def _adjust_size(self):
        doc = self.text_edit.document()
        doc_size = doc.size()
        w = max(240, int(doc_size.width()) + 36)
        h = max(70, int(doc_size.height()) + 28)
        self.resize(w, h)

    def _on_text_changed(self):
        self._adjust_size()

    def update_screen_position(self):
        transform = self.canvas_widget._get_canvas_transform()
        screen_pt = transform.map(self.canvas_pos)
        self.move(int(screen_pt.x()), int(screen_pt.y()))

    def get_text(self) -> str:
        return self.text_edit.toPlainText()

    def eventFilter(self, obj, event):
        if obj == self.text_edit and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Return and (event.modifiers() & QtCore.Qt.ControlModifier):
                self.canvas_widget.commit_text_overlay()
                return True
            if event.key() == QtCore.Qt.Key_Escape:
                self.canvas_widget.cancel_text_overlay()
                return True
        return super().eventFilter(obj, event)
