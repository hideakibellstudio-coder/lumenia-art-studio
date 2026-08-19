import os
import json
import logging
import re
from PySide6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)

class ThemeManager(QtCore.QObject):
    themeChanged = QtCore.Signal(str)  # Emite o nome do novo tema ("dark_default", etc.)

    _instance = None

    ALIASES = {
        "bg_main": "BG_DARKEST",
        "bg_panel": "BG_DARKER",
        "border": "BORDER",
        "border_color": "BORDER",
        "border_control": "BORDER_LIGHT",
        "text_main": "FG_PRIMARY",
        "text_sec": "FG_SECONDARY",
        "accent": "ACCENT",
        "accent_hover": "ACCENT_HOVER",
        "accent_bg": "ACCENT_MUTED",
        "accent_muted": "ACCENT_MUTED",
        "bg_hover": "BG_TERTIARY",
        "bg_mid": "BG_MID",
        "slider_groove": "BG_DARK",
        "slider_handle": "ACCENT"
    }
    REVERSE_ALIASES = {v: k for k, v in ALIASES.items()}

    DEFAULT_METRICS = {
        "RADIUS_SMALL": "4px",
        "RADIUS_MEDIUM": "6px",
        "RADIUS_LARGE": "8px",
        "FONT_FAMILY": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif"
    }

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._current_theme = "dark_default"
        self._themes = {}
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.themes_dir = os.path.join(self.base_dir, "themes")
        self.modules_dir = os.path.join(self.themes_dir, "qss_modules")
        
        # Caminho absoluto da pasta assets na raiz
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(self.base_dir)))
        self.assets_dir = os.path.join(project_root, "assets").replace("\\", "/")
        
        self.load_all_themes()

    def load_all_themes(self):
        """Carrega dinamicamente todos os temas em formato JSON na pasta 'themes'."""
        if not os.path.exists(self.themes_dir):
            logger.warning(f"ThemeManager: Pasta de temas não encontrada: {self.themes_dir}")
            return

        for fname in os.listdir(self.themes_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.themes_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    theme_key = fname.replace(".json", "")
                    self._themes[theme_key] = {
                        "file": theme_key,
                        "metadata": data.get("metadata", {}),
                        "colors": data.get("colors", {}),
                        "metrics": data.get("metrics", {})
                    }
                except Exception as e:
                    logger.error(f"ThemeManager: Falha ao carregar tema {fname}: {e}")

        # Garante fallback se nenhum tema foi carregado
        if not self._themes:
            self._themes["dark_default"] = {
                "file": "dark_default",
                "metadata": {"name": "Dark Premium (Slate)", "type": "dark"},
                "colors": {
                    "bg_main": "#0f172a",
                    "bg_panel": "#1e293b",
                    "border": "#334155",
                    "border_control": "#475569",
                    "text_main": "#f8fafc",
                    "text_sec": "#94a3b8",
                    "accent": "#3b82f6",
                    "accent_hover": "#60a5fa",
                    "accent_bg": "#1e3a8a",
                    "slider_groove": "#1e293b",
                    "slider_handle": "#3b82f6"
                },
                "metrics": {
                    "RADIUS_SMALL": "4px",
                    "RADIUS_MEDIUM": "6px",
                    "RADIUS_LARGE": "8px",
                    "FONT_FAMILY": "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif"
                }
            }

    def get_available_themes(self) -> list:
        """Retorna uma lista ordenada dos temas disponíveis para a UI de configurações."""
        return sorted(list(self._themes.values()), key=lambda t: t["metadata"].get("name", t["file"]))

    @property
    def current_theme(self) -> str:
        return self._current_theme

    @property
    def is_dark(self) -> bool:
        """Retorna True se o tema atual for dark (padrão)."""
        theme_info = self._themes.get(self._current_theme, {})
        return theme_info.get("metadata", {}).get("type", "dark") == "dark"

    def set_theme(self, theme_name: str):
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name: str):
        """Aplica o tema ativo e atualiza a folha de estilos global da QApplication."""
        if theme_name in self._themes and theme_name != self._current_theme:
            self._current_theme = theme_name
            
            # Aplica folha de estilos globalmente
            app = QtWidgets.QApplication.instance()
            if app:
                app.setStyleSheet(self.get_stylesheet())
                
            self.themeChanged.emit(theme_name)
            logger.info(f"ThemeManager: Tema '{theme_name}' aplicado com sucesso.")

    def toggle_theme(self):
        """Alterna de forma simples entre o primeiro tema de tipo light e dark encontrado."""
        current_type = self._themes.get(self._current_theme, {}).get("metadata", {}).get("type", "dark")
        target_type = "light" if current_type == "dark" else "dark"
        
        for key, theme in self._themes.items():
            if theme["metadata"].get("type") == target_type:
                self.apply_theme(key)
                break

    def compile_qss(self, template: str) -> str:
        """Permite a compilação pública de trechos de QSS customizados com tokens de tema."""
        return self._compile_qss(template)

    def get_stylesheet(self) -> str:
        """Gera a folha de estilo QSS formatando o template modular ou estático."""
        qss_template = self._load_qss_template()
        if not qss_template:
            # Fallback para o template estático se os módulos QSS não existirem
            from .palettes import QSS_TEMPLATE
            qss_template = QSS_TEMPLATE
            
        return self._compile_qss(qss_template)

    def _load_qss_template(self) -> str:
        """Lê todos os arquivos .qss dentro de 'qss_modules' em ordem alfabética e concatena."""
        compiled_template = ""
        if os.path.exists(self.modules_dir) and os.path.isdir(self.modules_dir):
            qss_files = sorted([f for f in os.listdir(self.modules_dir) if f.endswith('.qss')])
            for file_name in qss_files:
                file_path = os.path.join(self.modules_dir, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        compiled_template += f"\n/* --- Módulo: {file_name} --- */\n"
                        compiled_template += f.read() + "\n"
                except Exception as e:
                    logger.warning(f"ThemeManager: Falha ao ler módulo QSS {file_name}: {e}")
        return compiled_template

    def _compile_qss(self, template: str) -> str:
        """Substitui os marcadores @VARIAVEL pelos valores do JSON resolvido."""
        theme = self._themes.get(self._current_theme, self._themes.get("dark_default"))
        colors = theme.get("colors", {})
        metrics = theme.get("metrics", {})

        def replace_token(match):
            token = match.group(1)
            if token == "ASSETS_DIR":
                return self.assets_dir
            elif token in metrics:
                return metrics[token]
            elif token in self.DEFAULT_METRICS:
                return self.DEFAULT_METRICS[token]
            else:
                return self.resolve_color(token, colors)

        compiled = re.sub(r'@([A-Za-z0-9_]+)', replace_token, template)

        # Regra de escala (HiDPI)
        scale = 1.0
        # Simula escala simples
        if scale != 1.0:
            def scale_match(match):
                value = float(match.group(1))
                unit = match.group(2)
                scaled_value = round(value * scale)
                if value == 0:
                    return f"0{unit}"
                return f"{scaled_value}{unit}"
            compiled = re.sub(r'(\d+(?:\.\d+)?)\s*(px|pt)', scale_match, compiled)

        return compiled

    def resolve_color(self, token: str, colors: dict) -> str:
        """Resolve a cor do token lidando com aliases de compatibilidade de case."""
        # 1. Busca direta (exata)
        if token in colors:
            return colors[token]
            
        # 2. Busca em minúsculo
        lower_token = token.lower()
        if lower_token in colors:
            return colors[lower_token]
            
        # 3. Busca por Alias
        alias = self.ALIASES.get(lower_token)
        if alias and alias in colors:
            return colors[alias]
            
        # 4. Busca por Alias Reverso
        rev_alias = self.REVERSE_ALIASES.get(token)
        if rev_alias and rev_alias in colors:
            return colors[rev_alias]
            
        # Fallback de correspondência de mapa
        fallback_map = {
            "BG_DARKEST": "bg_main",
            "BG_DARKER": "bg_panel",
            "BG_DARK": "slider_groove",
            "BG_MID": "bg_panel",
            "BG_TERTIARY": "border",
            "BG_LIGHT": "bg_panel",
            "BG_LIGHTER": "border",
            "BG_LIGHTEST": "border_control",
            "FG_PRIMARY": "text_main",
            "FG_SECONDARY": "text_sec",
            "FG_TERTIARY": "text_sec",
            "FG_LINK": "accent",
            "ACCENT": "accent",
            "ACCENT_HOVER": "accent_hover",
            "ACCENT_MUTED": "accent_bg",
            "BORDER": "border",
            "BORDER_LIGHT": "border_control",
            "SLIDER_GROOVE": "slider_groove",
            "SLIDER_HANDLE": "slider_handle",
            "BORDER_CONTROL": "border_control"
        }
        fb_token = fallback_map.get(token)
        if fb_token and fb_token in colors:
            return colors[fb_token]

        return "#000000"

    def get_color(self, name: str, fallback: str = "#000000") -> str:
        """Retorna a cor Hex correspondente ao token solicitado com fallback opcional."""
        theme = self._themes.get(self._current_theme, self._themes.get("dark_default", {}))
        if not theme:
            return fallback
        colors = theme.get("colors", {})
        res = self.resolve_color(name, colors)
        return res if res != "#000000" else fallback

