"""Dynamic Engine Parameters Widget for ALADYN engines."""

from PySide6 import QtWidgets
from ui.core.widgets.slider import LabeledSlider
from ui.core.engine.registry import EngineRegistry

class DynamicEngineParamsWidget(QtWidgets.QWidget):
    """Container dinâmico que exibe os sliders exclusivos de cada mini-motor C++."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self._current_engine_type = 0
        self._build_empty()

    def _build_empty(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def set_engine_type(self, engine_type: int):
        self._current_engine_type = engine_type
        self._build_empty()

        backend = EngineRegistry.instance().get_backend()

        if engine_type == 1:  # Pencil
            lbl = QtWidgets.QLabel("Parâmetros de Lápis & Carvão")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_hard = LabeledSlider("Dureza do Grafite (2H-6B):", 1, 100, 50, "%")
            sl_hard.valueChanged.connect(lambda v: self._set_pencil_hard(backend, v / 100.0))
            self.layout.addWidget(sl_hard)

            chk_tilt = QtWidgets.QCheckBox("Sombra por Inclinação (Tilt Shading)")
            chk_tilt.stateChanged.connect(lambda s: self._set_pencil_tilt(backend, chk_tilt.isChecked()))
            self.layout.addWidget(chk_tilt)

        elif engine_type == 2:  # Inker
            lbl = QtWidgets.QLabel("Parâmetros de Caneta & Nanquim")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_flow = LabeledSlider("Taxa de Vazão (Ink Flow):", 1, 100, 100, "%")
            sl_flow.valueChanged.connect(lambda v: self._set_inker_flow(backend, v / 100.0))
            self.layout.addWidget(sl_flow)

            sl_taper = LabeledSlider("Suavização (Taper Smoothing):", 0, 100, 70, "%")
            sl_taper.valueChanged.connect(lambda v: self._set_inker_taper(backend, v / 100.0))
            self.layout.addWidget(sl_taper)

        elif engine_type == 4:  # Marker
            lbl = QtWidgets.QLabel("Parâmetros de Marcador & Feltro")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_wet = LabeledSlider("Umidade do Solvente:", 0, 100, 60, "%")
            sl_wet.valueChanged.connect(lambda v: self._set_marker_wet(backend, v / 100.0))
            self.layout.addWidget(sl_wet)

            sl_edge = LabeledSlider("Escurecimento de Borda:", 0, 100, 40, "%")
            sl_edge.valueChanged.connect(lambda v: self._set_marker_edge(backend, v / 100.0))
            self.layout.addWidget(sl_edge)

        elif engine_type == 5:  # Blur
            lbl = QtWidgets.QLabel("Parâmetros de Blur / Desfoque")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_rad = LabeledSlider("Raio do Desfoque:", 1, 10, 2, "px")
            sl_rad.valueChanged.connect(lambda v: self._set_blur_radius(backend, int(v)))
            self.layout.addWidget(sl_rad)

            sl_str = LabeledSlider("Força do Blur:", 1, 100, 60, "%")
            sl_str.valueChanged.connect(lambda v: self._set_blur_strength(backend, v / 100.0))
            self.layout.addWidget(sl_str)

        elif engine_type == 6:  # Smudge
            lbl = QtWidgets.QLabel("Parâmetros de Smudge / Arrasto")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_pick = LabeledSlider("Coleta de Cor (Pickup):", 0, 100, 70, "%")
            sl_pick.valueChanged.connect(lambda v: self._set_smudge_pick(backend, v / 100.0))
            self.layout.addWidget(sl_pick)

            sl_mix = LabeledSlider("Razão de Mistura (Mix):", 0, 100, 50, "%")
            sl_mix.valueChanged.connect(lambda v: self._set_smudge_mix(backend, v / 100.0))
            self.layout.addWidget(sl_mix)

            sl_str = LabeledSlider("Arrasto da Cor (Stretch):", 0, 100, 80, "%")
            sl_str.valueChanged.connect(lambda v: self._set_smudge_stretch(backend, v / 100.0))
            self.layout.addWidget(sl_str)

        elif engine_type == 7:  # Watercolor
            lbl = QtWidgets.QLabel("Parâmetros de Aquarela Realista")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_water = LabeledSlider("Nível de Água (Water Level):", 0, 100, 80, "%")
            sl_water.valueChanged.connect(lambda v: self._set_wc_water(backend, v / 100.0))
            self.layout.addWidget(sl_water)

            sl_bleed = LabeledSlider("Sangria de Pigmento (Bleed):", 0, 100, 80, "%")
            sl_bleed.valueChanged.connect(lambda v: self._set_wc_bleed(backend, v / 100.0))
            self.layout.addWidget(sl_bleed)

            sl_fringe = LabeledSlider("Borda de Secagem (Fringe):", 0, 100, 30, "%")
            sl_fringe.valueChanged.connect(lambda v: self._set_wc_fringe(backend, v / 100.0))
            self.layout.addWidget(sl_fringe)

            sl_gran = LabeledSlider("Granulação do Papel:", 0, 100, 40, "%")
            sl_gran.valueChanged.connect(lambda v: self._set_wc_gran(backend, v / 100.0))
            self.layout.addWidget(sl_gran)

        elif engine_type == 8:  # OilImpasto
            lbl = QtWidgets.QLabel("Parâmetros de Óleo 3D & Impasto")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_depth = LabeledSlider("Profundidade 3D (Impasto):", 0, 100, 90, "%")
            sl_depth.valueChanged.connect(lambda v: self._set_oil_depth(backend, v / 100.0))
            self.layout.addWidget(sl_depth)

            sl_groove = LabeledSlider("Sulcos de Cerdas:", 0, 100, 80, "%")
            sl_groove.valueChanged.connect(lambda v: self._set_oil_grooves(backend, v / 100.0))
            self.layout.addWidget(sl_groove)

            sl_visc = LabeledSlider("Viscosidade da Tinta:", 0, 100, 80, "%")
            sl_visc.valueChanged.connect(lambda v: self._set_oil_visc(backend, v / 100.0))
            self.layout.addWidget(sl_visc)

            sl_spec = LabeledSlider("Brilho Especular:", 0, 100, 70, "%")
            sl_spec.valueChanged.connect(lambda v: self._set_oil_spec(backend, v / 100.0))
            self.layout.addWidget(sl_spec)

        else:
            lbl = QtWidgets.QLabel("Parâmetros de Borrifo / Spray (Pincel Básico)")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_scat = LabeledSlider("Contagem de Borrifos / Spray:", 1, 10, 1, "dabs")
            if backend and hasattr(backend, "_facade") and backend._facade:
                sl_scat.setValue(int(backend._facade.get_brush_profile().scatter_count))
            sl_scat.valueChanged.connect(lambda v: self._set_scatter_count(backend, int(v)))
            self.layout.addWidget(sl_scat)

        self.layout.addStretch()

    def _set_scatter_count(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().scatter_count = int(v)

    def _set_pencil_hard(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().pencil_params.graphite_hardness = float(v)

    def _set_pencil_tilt(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().pencil_params.tilt_shading_enabled = bool(v)

    def _set_inker_flow(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().inker_params.ink_flow_rate = float(v)

    def _set_inker_taper(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().inker_params.taper_smoothing = float(v)

    def _set_marker_wet(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().marker_params.solvent_wetness = float(v)

    def _set_marker_edge(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().marker_params.edge_darkening = float(v)

    def _set_blur_radius(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().blur_params.blur_radius = int(v)

    def _set_blur_strength(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().blur_params.blur_strength = float(v)

    def _set_smudge_pick(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().smudge_params.color_pickup = float(v)

    def _set_smudge_mix(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().smudge_params.mix_ratio = float(v)

    def _set_smudge_stretch(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().smudge_params.smudge_stretch = float(v)

    def _set_wc_water(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.water_level = float(v)

    def _set_wc_bleed(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.pigment_bleed = float(v)

    def _set_wc_fringe(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.fringe_intensity = float(v)

    def _set_wc_gran(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.granulation = float(v)

    def _set_oil_depth(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.impasto_depth = float(v)

    def _set_oil_grooves(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.bristle_grooves = float(v)

    def _set_oil_visc(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.viscosity = float(v)

    def _set_oil_spec(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.specular_brilliance = float(v)
