"""Canonical IDs and factory keyboard shortcuts."""

DEFAULT_SHORTCUTS = [
    # Categoria: Ferramentas
    {"id": "tool_brush", "category": "Ferramentas", "name": "Ferramenta Pincel", "default": "B", "icon": "brush"},
    {"id": "tool_eraser", "category": "Ferramentas", "name": "Ferramenta Borracha", "default": "E", "icon": "eraser"},
    {"id": "tool_shapes", "category": "Ferramentas", "name": "Ferramenta Formas Geométricas", "default": "U", "icon": "shapes"},
    {"id": "tool_text", "category": "Ferramentas", "name": "Ferramenta de Texto", "default": "T", "icon": "text"},
    {"id": "tool_eyedropper", "category": "Ferramentas", "name": "Conta-Gotas", "default": "I", "icon": "eyedropper"},
    {"id": "tool_fill", "category": "Ferramentas", "name": "Balde de Tinta (Preenchimento)", "default": "G", "icon": "bucket"},
    {"id": "tool_wand", "category": "Ferramentas", "name": "Varinha Mágica", "default": "W", "icon": "wand"},
    {"id": "tool_transform", "category": "Ferramentas", "name": "Transformação Livre", "default": "Ctrl+T", "icon": "transform"},

    # Categoria: Arquivo
    {"id": "file_new", "category": "Arquivo", "name": "Novo Documento", "default": "Ctrl+N", "icon": "plus"},
    {"id": "file_open", "category": "Arquivo", "name": "Abrir Imagem / Documento", "default": "Ctrl+O", "icon": "folder"},
    {"id": "file_save", "category": "Arquivo", "name": "Salvar", "default": "Ctrl+S", "icon": "save"},
    {"id": "file_save_as", "category": "Arquivo", "name": "Salvar Como...", "default": "Ctrl+Shift+S", "icon": "save"},
    {"id": "file_export", "category": "Arquivo", "name": "Exportar Imagem...", "default": "Ctrl+E", "icon": "export"},
    {"id": "file_close", "category": "Arquivo", "name": "Fechar Aba Atual", "default": "Ctrl+W", "icon": "close"},
    {"id": "file_exit", "category": "Arquivo", "name": "Sair do Lumenia", "default": "Ctrl+Q", "icon": "close"},

    # Categoria: Edição
    {"id": "edit_undo", "category": "Edição", "name": "Desfazer (Undo)", "default": "Ctrl+Z", "icon": "undo"},
    {"id": "edit_redo", "category": "Edição", "name": "Refazer (Redo)", "default": "Ctrl+Y", "icon": "redo"},
    {"id": "edit_cut", "category": "Edição", "name": "Recortar", "default": "Ctrl+X", "icon": "cut"},
    {"id": "edit_copy", "category": "Edição", "name": "Copiar", "default": "Ctrl+C", "icon": "copy"},
    {"id": "edit_paste", "category": "Edição", "name": "Colar", "default": "Ctrl+V", "icon": "paste"},
    {"id": "edit_clear_layer", "category": "Edição", "name": "Limpar Conteúdo da Camada", "default": "Del", "icon": "clean_layer"},

    # Categoria: Camadas
    {"id": "layer_new", "category": "Camadas", "name": "Nova Camada", "default": "Ctrl+Shift+N", "icon": "plus"},
    {"id": "layer_group", "category": "Camadas", "name": "Novo Grupo", "default": "Ctrl+G", "icon": "folder"},
    {"id": "layer_duplicate", "category": "Camadas", "name": "Duplicar Camada / Grupo", "default": "Ctrl+J", "icon": "duplicate"},
    {"id": "layer_delete", "category": "Camadas", "name": "Excluir Camada Ativa", "default": "Shift+Del", "icon": "trash"},
    {"id": "layer_merge", "category": "Camadas", "name": "Mesclar Camada para Baixo", "default": "Ctrl+Shift+E", "icon": "layer_flatten"},

    # Categoria: Exibir
    {"id": "view_zoom_in", "category": "Exibir", "name": "Aproximar Zoom (Zoom In)", "default": "Ctrl+=", "icon": "zoom_in"},
    {"id": "view_zoom_out", "category": "Exibir", "name": "Afastar Zoom (Zoom Out)", "default": "Ctrl+-", "icon": "zoom_out"},
    {"id": "view_zoom_100", "category": "Exibir", "name": "Resetar Zoom para 100%", "default": "Ctrl+0", "icon": "reset"},
    {"id": "view_reset_rot", "category": "Exibir", "name": "Resetar Rotação da Câmera", "default": "Ctrl+R", "icon": "reset"},
    {"id": "view_grid", "category": "Exibir", "name": "Alternar Grade Guia", "default": "Ctrl+'", "icon": "grid"},

    # Categoria: Seleção
    {"id": "select_all", "category": "Seleção", "name": "Selecionar Tudo", "default": "Ctrl+A", "icon": "select"},
    {"id": "select_deselect", "category": "Seleção", "name": "Desmarcar Seleção", "default": "Ctrl+D", "icon": "deselect"},
    {"id": "select_invert", "category": "Seleção", "name": "Inverter Seleção", "default": "Ctrl+Shift+I", "icon": "transform"},
]

# O catálogo separa comandos de janela dos que pertencem à superfície de
# pintura. A informação é usada pelo registro para preservar a edição de texto
# e deixar os atalhos que o canvas trata localmente chegarem ao InputRouter.
CANVAS_SHORTCUT_IDS = frozenset({
    "tool_brush", "tool_eraser", "tool_shapes", "tool_text",
    "tool_eyedropper", "tool_fill", "tool_wand", "tool_transform",
    "select_all", "select_deselect", "select_invert",
})
for _shortcut_definition in DEFAULT_SHORTCUTS:
    _shortcut_definition["context"] = (
        "canvas" if _shortcut_definition["id"] in CANVAS_SHORTCUT_IDS else "window"
    )
del _shortcut_definition
