"""Dynamic Engine Parameters Widget for ALADYN engines."""

from PySide6 import QtWidgets
from ui.core.widgets.slider import LabeledSlider
from ui.core.engine.engine_type import EngineType
from ui.core.engine.registry import EngineRegistry
from ui.infrastructure.i18n import tr, I18nManager

class DynamicEngineParamsWidget(QtWidgets.QWidget):
    """Container dinâmico que exibe os sliders exclusivos de cada mini-motor C++."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self._current_engine_type = EngineType.BRUSH
        self._build_empty()
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_empty(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def retranslate_ui(self):
        self.set_engine_type(self._current_engine_type)

    def _get_backend(self):
        return EngineRegistry.instance().get_backend()

    def set_engine_type(self, engine_type: int):
        self._current_engine_type = engine_type
        self._build_empty()

        backend = self._get_backend()

        if engine_type == EngineType.PENCIL:
            lbl = QtWidgets.QLabel(tr("engine_params.pencil_title", "Parâmetros de Lápis & Carvão"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_hard = LabeledSlider(f"{tr('engine_params.pencil_hard', 'Dureza do Grafite (2H-6B)')}:", 1, 100, 50, "%")
            sl_hard.valueChanged.connect(lambda v: self._set_pencil_hard(v / 100.0))
            self.layout.addWidget(sl_hard)

            chk_tilt = QtWidgets.QCheckBox(tr("engine_params.pencil_tilt", "Sombra por Inclinação (Tilt Shading)"))
            chk_tilt.stateChanged.connect(lambda s: self._set_pencil_tilt(chk_tilt.isChecked()))
            self.layout.addWidget(chk_tilt)

        elif engine_type == EngineType.INKER:
            lbl = QtWidgets.QLabel(tr("engine_params.inker_title", "Parâmetros de Caneta & Nanquim"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_flow = LabeledSlider(f"{tr('engine_params.inker_flow', 'Taxa de Vazão (Ink Flow)')}:", 1, 100, 100, "%")
            sl_flow.valueChanged.connect(lambda v: self._set_inker_flow(v / 100.0))
            self.layout.addWidget(sl_flow)

            sl_taper = LabeledSlider(f"{tr('engine_params.inker_taper', 'Suavização (Taper Smoothing)')}:", 0, 100, 70, "%")
            sl_taper.valueChanged.connect(lambda v: self._set_inker_taper(v / 100.0))
            self.layout.addWidget(sl_taper)

        elif engine_type == EngineType.MARKER:
            lbl = QtWidgets.QLabel(tr("engine_params.marker_title", "Parâmetros de Marcador & Feltro"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_wet = LabeledSlider(f"{tr('engine_params.marker_wet', 'Umidade do Solvente')}:", 0, 100, 60, "%")
            sl_wet.valueChanged.connect(lambda v: self._set_marker_wet(v / 100.0))
            self.layout.addWidget(sl_wet)

            sl_edge = LabeledSlider(f"{tr('engine_params.marker_edge', 'Escurecimento de Borda')}:", 0, 100, 40, "%")
            sl_edge.valueChanged.connect(lambda v: self._set_marker_edge(v / 100.0))
            self.layout.addWidget(sl_edge)

        elif engine_type == EngineType.BLUR:
            lbl = QtWidgets.QLabel(tr("engine_params.blur_title", "Parâmetros de Blur / Desfoque"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_rad = LabeledSlider(f"{tr('engine_params.blur_radius', 'Raio do Desfoque')}:", 1, 10, 2, "px")
            sl_rad.valueChanged.connect(lambda v: self._set_blur_radius(int(v)))
            self.layout.addWidget(sl_rad)

            sl_str = LabeledSlider(f"{tr('engine_params.blur_strength', 'Força do Blur')}:", 1, 100, 60, "%")
            sl_str.valueChanged.connect(lambda v: self._set_blur_strength(v / 100.0))
            self.layout.addWidget(sl_str)

        elif engine_type == EngineType.SMUDGE:
            lbl = QtWidgets.QLabel(tr("engine_params.smudge_title", "Parâmetros de Smudge / Arrasto"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_pick = LabeledSlider(f"{tr('engine_params.smudge_pick', 'Coleta de Cor (Pickup)')}:", 0, 100, 70, "%")
            sl_pick.valueChanged.connect(lambda v: self._set_smudge_pick(v / 100.0))
            self.layout.addWidget(sl_pick)

            sl_mix = LabeledSlider(f"{tr('engine_params.smudge_mix', 'Razão de Mistura (Mix)')}:", 0, 100, 50, "%")
            sl_mix.valueChanged.connect(lambda v: self._set_smudge_mix(v / 100.0))
            self.layout.addWidget(sl_mix)

            sl_str = LabeledSlider(f"{tr('engine_params.smudge_stretch', 'Arrasto da Cor (Stretch)')}:", 0, 100, 80, "%")
            sl_str.valueChanged.connect(lambda v: self._set_smudge_stretch(v / 100.0))
            self.layout.addWidget(sl_str)

        elif engine_type == EngineType.WATERCOLOR:
            lbl = QtWidgets.QLabel(tr("engine_params.watercolor_title", "Parâmetros de Aquarela Realista"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_water = LabeledSlider(f"{tr('engine_params.wc_water', 'Nível de Água (Water Level)')}:", 0, 100, 80, "%")
            sl_water.valueChanged.connect(lambda v: self._set_wc_water(v / 100.0))
            self.layout.addWidget(sl_water)

            sl_bleed = LabeledSlider(f"{tr('engine_params.wc_bleed', 'Sangria de Pigmento (Bleed)')}:", 0, 100, 80, "%")
            sl_bleed.valueChanged.connect(lambda v: self._set_wc_bleed(v / 100.0))
            self.layout.addWidget(sl_bleed)

            sl_fringe = LabeledSlider(f"{tr('engine_params.wc_fringe', 'Borda de Secagem (Fringe)')}:", 0, 100, 30, "%")
            sl_fringe.valueChanged.connect(lambda v: self._set_wc_fringe(v / 100.0))
            self.layout.addWidget(sl_fringe)

            sl_gran = LabeledSlider(f"{tr('engine_params.wc_gran', 'Granulação do Papel')}:", 0, 100, 40, "%")
            sl_gran.valueChanged.connect(lambda v: self._set_wc_gran(v / 100.0))
            self.layout.addWidget(sl_gran)

        elif engine_type == EngineType.OIL_IMPASTO:
            lbl = QtWidgets.QLabel(tr("engine_params.oil_title", "Parâmetros de Óleo 3D & Impasto"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_depth = LabeledSlider(f"{tr('engine_params.oil_depth', 'Profundidade 3D (Impasto)')}:", 0, 100, 90, "%")
            sl_depth.valueChanged.connect(lambda v: self._set_oil_depth(v / 100.0))
            self.layout.addWidget(sl_depth)

            sl_groove = LabeledSlider(f"{tr('engine_params.oil_grooves', 'Sulcos de Cerdas')}:", 0, 100, 80, "%")
            sl_groove.valueChanged.connect(lambda v: self._set_oil_grooves(v / 100.0))
            self.layout.addWidget(sl_groove)

            sl_visc = LabeledSlider(f"{tr('engine_params.oil_viscosity', 'Viscosidade da Tinta')}:", 0, 100, 80, "%")
            sl_visc.valueChanged.connect(lambda v: self._set_oil_visc(v / 100.0))
            self.layout.addWidget(sl_visc)

            sl_spec = LabeledSlider(f"{tr('engine_params.oil_specular', 'Brilho Especular')}:", 0, 100, 70, "%")
            sl_spec.valueChanged.connect(lambda v: self._set_oil_spec(v / 100.0))
            self.layout.addWidget(sl_spec)

        else:
            lbl = QtWidgets.QLabel(tr("engine_params.basic_scatter", "Parâmetros de Borrifo / Spray (Pincel Básico)"))
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_scat = LabeledSlider(f"{tr('engine_params.scatter_count', 'Contagem de Borrifos / Spray')}:", 1, 10, 1, "dabs")
            if backend:
                prof_data = backend.get_brush_profile_dict()
                sl_scat.setValue(int(prof_data.get("scatter_count", 1)))
            sl_scat.valueChanged.connect(lambda v: self._set_scatter_count(int(v)))
            self.layout.addWidget(sl_scat)

        self.layout.addStretch()

    def _set_scatter_count(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("root", "scatter_count", int(v))

    def _set_pencil_hard(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("pencil", "graphite_hardness", float(v))

    def _set_pencil_tilt(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("pencil", "tilt_shading_enabled", bool(v))

    def _set_inker_flow(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("inker", "ink_flow_rate", float(v))

    def _set_inker_taper(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("inker", "taper_smoothing", float(v))

    def _set_marker_wet(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("marker", "solvent_wetness", float(v))

    def _set_marker_edge(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("marker", "edge_darkening", float(v))

    def _set_blur_radius(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("blur", "blur_radius", int(v))

    def _set_blur_strength(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("blur", "blur_strength", float(v))

    def _set_smudge_pick(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("smudge", "color_pickup", float(v))

    def _set_smudge_mix(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("smudge", "mix_ratio", float(v))

    def _set_smudge_stretch(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("smudge", "smudge_stretch", float(v))

    def _set_wc_water(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("watercolor", "water_level", float(v))

    def _set_wc_bleed(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("watercolor", "pigment_bleed", float(v))

    def _set_wc_fringe(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("watercolor", "fringe_intensity", float(v))

    def _set_wc_gran(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("watercolor", "granulation", float(v))

    def _set_oil_depth(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("oil", "impasto_depth", float(v))

    def _set_oil_grooves(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("oil", "bristle_grooves", float(v))

    def _set_oil_visc(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("oil", "viscosity", float(v))

    def _set_oil_spec(self, v):
        b = self._get_backend()
        if b: b.set_brush_param("oil", "specular_brilliance", float(v))
