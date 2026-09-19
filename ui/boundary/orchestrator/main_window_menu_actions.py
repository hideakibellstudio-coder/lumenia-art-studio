"""MainWindowMenuActionsMixin — Handlers de Ações da MenuBar para MainWindow."""

from __future__ import annotations
import os
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.modify_selection_dialog import ModifySelectionDialog
from ui.core.dialogs.layer_properties_dialog import LayerPropertiesDialog
from .main_window_dialog_actions import MainWindowDialogActionsMixin
from .main_window_document_actions import MainWindowDocumentActionsMixin


from ui.core.document.history import layer_transaction

from .main_window_image_actions import MainWindowImageActionsMixin

class MainWindowMenuActionsMixin(
    MainWindowDocumentActionsMixin,
    MainWindowDialogActionsMixin,
    MainWindowImageActionsMixin
):
    """Mixin com todos os manipuladores de ações da MenuBar do Lumenia."""

    # ── 1. Área de Transferência (Clipboard) ──────────────────────────────

    def copy_selection_or_layer_to_clipboard(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return
        qimg = backend.get_qimage()
        if qimg and not qimg.isNull():
            QtWidgets.QApplication.clipboard().setImage(qimg)
            self.status_bar.showMessage("Camada / Imagem copiada para a Área de Transferência.", 2500)

    def cut_selection_or_layer_to_clipboard(self) -> None:
        self.copy_selection_or_layer_to_clipboard()
        backend = EngineRegistry.instance().get_backend()
        if backend and backend.has_selection():
            if True:
                backend.delete_selection_on_active_layer()
        else:
            self.clear_active_layer()
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.status_bar.showMessage("Cortado para a Área de Transferência.", 2500)

    def paste_clipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        qimg = clipboard.image()
        if not qimg.isNull():
            qimg_rgba = qimg.convertToFormat(QtGui.QImage.Format_RGBA8888)
            w, h = qimg_rgba.width(), qimg_rgba.height()
            raw_bytes = bytes(qimg_rgba.constBits()[:w * h * 4])

            backend = EngineRegistry.instance().get_backend()
            if backend and getattr(backend, "available", False):
                backend.paste_rgba_buffer_on_active_layer(0, 0, w, h, raw_bytes)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage(f"Imagem ({w}×{h}) colada na camada ativa.", 2500)
            else:
                doc = self.dm.new_document(width=w, height=h, name="Colado")
                self.status_bar.showMessage(f"Imagem ({w}×{h}) colada em novo documento.", 2500)
        else:
            self.status_bar.showMessage("Nenhuma imagem encontrada na Área de Transferência.", 2000)

    def fill_active_selection_or_canvas(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return
        color = getattr(self.workspace, "_saved_color", QtGui.QColor("#000000")) if self.workspace else QtGui.QColor("#000000")
        if backend and backend.has_selection():
            if True:
                backend.fill_selection_on_active_layer(color)
        else:
            backend.fill_area(0, 0, color, tolerance=255, contiguous=False)
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.status_bar.showMessage("Preenchimento aplicado.", 2000)

    # ── 2. Seleção ────────────────────────────────────────────────────────

    def select_all(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.select_all()
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Tudo selecionado.", 2000)

    def invert_selection(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.invert_selection()
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Seleção invertida.", 2000)

    def open_modify_selection_dialog(self, mode: str) -> None:
        dialog = ModifySelectionDialog(mode=mode, parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            px = dialog.get_pixels()
            self.status_bar.showMessage(f"Seleção modificada ({mode}: {px} px).", 2000)

    # ── 3. Camadas ────────────────────────────────────────────────────────

    def _active_layer_context(self):
        doc = self.dm.active_document()
        if not doc or not hasattr(doc, "layer_manager"):
            return None, None, None, -1
        lm = doc.layer_manager
        layer = lm.get_active_layer()
        idx = lm.active_index
        backend = EngineRegistry.instance().get_backend()
        return doc, lm, backend, idx

    @staticmethod
    def _backend_ready(backend) -> bool:
        return bool(backend and getattr(backend, "available", False))

    def _refresh_canvas(self) -> None:
        if self.workspace:
            self.workspace.canvas_widget.update()

    @layer_transaction
    def clear_active_layer(self) -> None:
        """Limpa o conteudo (pixels) da camada ativa, preservando a propria camada.

        Handler unico para toda acao de "limpar" exposta na interface
        (Editar > Limpar Conteudo da Camada, Tool Sidebar, e o fallback de
        Cortar sem selecao). A acao equivalente que existia em Arquivo >
        Limpar foi removida por ser um acesso duplicado ao mesmo handler;
        Editar e o unico ponto de entrada agora. Nao existe mais um caminho
        de "limpar o canvas inteiro / todas as camadas" na UI -- ver
        panorama claude/panorama-menu-bar-fluxo-navigator.md.
        """
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        if self._backend_ready(backend):
            backend.clear_layer(act_idx)
        self._refresh_canvas()
        self.status_bar.showMessage("Conteudo da camada ativa limpo.", 2000)

    def toggle_soft_proof(self, enabled: bool) -> None:
        """Liga/desliga a prova de cores (soft-proofing) sem abrir dialogo.

        Handler do toggle leve exposto em Exibir > Prova de Cores (ver
        claude/panorama-menu-bar-fluxo-navigator.md). Reaproveita o
        SoftProofConfig ja mantido pelo backend -- so alterna o campo
        'enabled', preservando perfil/intent/gamut configurados no
        RenderSettingsDialog (Configuracoes > Renderizacao & Modos de Cor,
        que continua sendo o unico lugar para ajustar esses detalhes).
        """
        backend = EngineRegistry.instance().get_backend()
        if not self._backend_ready(backend):
            return
        config = backend.get_soft_proofing()
        config.enabled = bool(enabled)
        backend.set_soft_proofing(config)
        self._refresh_canvas()
        msg = "Prova de cores ativada." if enabled else "Prova de cores desativada."
        self.status_bar.showMessage(msg, 2000)

    @layer_transaction
    def create_new_layer(self) -> None:
        doc, lm, backend, idx = self._active_layer_context()
        if not lm:
            return
        insert_index = idx + 1 if idx >= 0 else -1
        if self._backend_ready(backend):
            native_idx = backend.add_layer("Nova Camada", insert_index)
            if native_idx < 0:
                self.status_bar.showMessage("Não foi possível criar a camada no motor.", 2500)
                return
        # lm.add_layer() já sincroniza a seleção com o motor via sync_backend_add
        # (Achado #2 do panorama de auditoria profunda de camadas: era uma
        # segunda chamada nativa redundante a backend.select_layer()).
        uid = lm.add_layer("Nova Camada")
        if not uid:
            # A mutacao nativa acima ja aconteceu. Sem este raise a funcao
            # retornaria normalmente e a transacao cairia no guard generico de
            # contagem de DocumentHistory.transaction ("camadas divergentes entre
            # documento e motor"): o rollback esta certo, mas a mensagem esconde a
            # causa real. Levantar aqui produz o mesmo rollback com o motivo certo.
            raise RuntimeError("Não foi possível criar a camada no documento.")
        self._refresh_canvas()
        self.status_bar.showMessage("Nova camada criada.", 2000)

    @layer_transaction
    def create_new_group(self) -> None:
        doc, lm, backend, idx = self._active_layer_context()
        if not lm:
            return
        insert_index = idx + 1 if idx >= 0 else -1
        if self._backend_ready(backend):
            native_idx = backend.add_group("Novo Grupo", insert_index)
            if native_idx < 0:
                self.status_bar.showMessage("Não foi possível criar o grupo no motor.", 2500)
                return
        # lm.add_group() já sincroniza a seleção com o motor via sync_backend_add
        # (ver Achado #2 do panorama de auditoria profunda de camadas).
        uid = lm.add_group("Novo Grupo")
        if not uid:
            # Mesmo motivo do raise em create_new_layer.
            raise RuntimeError("Não foi possível criar o grupo no documento.")
        self._refresh_canvas()
        self.status_bar.showMessage("Novo grupo de camadas criado.", 2000)

    @layer_transaction
    def duplicate_active_layer(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        if self._backend_ready(backend) and backend.duplicate_layer(act_idx) < 0:
            self.status_bar.showMessage("Não foi possível duplicar a camada no motor.", 2500)
            return
        # lm.duplicate_layer() já sincroniza a seleção com o motor via
        # sync_backend_duplicate (ver Achado #2 do panorama de auditoria
        # profunda de camadas).
        active = lm.get_active_layer()
        if not (active and lm.duplicate_layer(active.uid)):
            # Mesmo motivo do raise em create_new_layer.
            raise RuntimeError("Não foi possível duplicar a camada no documento.")
        self._refresh_canvas()
        self.status_bar.showMessage("Camada duplicada.", 2000)

    @layer_transaction
    def delete_active_layer(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        active = lm.get_active_layer()
        if not active:
            return
        if self._backend_ready(backend) and not backend.remove_layer(act_idx):
            self.status_bar.showMessage("Não foi possível remover a camada no motor.", 2500)
            return
        # lm.remove_layer() já sincroniza a seleção com o motor via
        # sync_backend_remove (ver Achado #2 do panorama de auditoria
        # profunda de camadas).
        if not lm.remove_layer(active.uid):
            # Mesmo motivo do raise em create_new_layer.
            raise RuntimeError("Não foi possível remover a camada do documento.")
        self._refresh_canvas()
        self.status_bar.showMessage("Camada removida.", 2000)

    @layer_transaction
    def merge_layer_down(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx <= 0:
            return
        active = lm.get_active_layer()
        if not active:
            return
        if self._backend_ready(backend) and not backend.merge_layer_down(act_idx):
            self.status_bar.showMessage("Não foi possível mesclar a camada no motor.", 2500)
            return
        # lm.merge_down() já sincroniza a seleção com o motor via
        # sync_backend_merge_down (ver Achado #2 do panorama de auditoria
        # profunda de camadas).
        if not lm.merge_down(active.uid):
            # Mesmo motivo do raise em create_new_layer.
            raise RuntimeError("Não foi possível mesclar a camada no documento.")
        self._refresh_canvas()
        self.status_bar.showMessage("Camada mesclada para baixo.", 2000)

    @layer_transaction
    def toggle_active_layer_clipping(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        curr = bool(getattr(layer, "clipping_mask", False))
        value = not curr
        # lm.set_clipping_mask() já sincroniza com o motor via sync_backend_property;
        # a chamada direta a backend.set_layer_clipping_mask() era uma segunda
        # composição completa do canvas, sem guard (Achado #2 do panorama de
        # auditoria profunda de camadas).
        lm.set_clipping_mask(act_idx, value)
        self._refresh_canvas()
        state_str = "ativada" if value else "desativada"
        self.status_bar.showMessage(f"Máscara de corte {state_str}.", 2000)

    @layer_transaction
    def toggle_active_layer_alpha_lock(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        curr = bool(getattr(layer, "alpha_locked", False))
        value = not curr
        # lm.set_alpha_lock() já sincroniza com o motor via sync_backend_property
        # (ver Achado #2 do panorama de auditoria profunda de camadas).
        lm.set_alpha_lock(act_idx, value)
        self._refresh_canvas()
        state_str = "ativado" if value else "desativado"
        self.status_bar.showMessage(f"Bloqueio Alpha {state_str}.", 2000)

    @layer_transaction
    def toggle_active_layer_visibility(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        curr = bool(getattr(layer, "visible", True))
        value = not curr
        # lm.set_layer_visibility() já sincroniza com o motor via
        # sync_backend_property (ver Achado #2 do panorama de auditoria
        # profunda de camadas).
        lm.set_layer_visibility(act_idx, value)
        self._refresh_canvas()
        state_str = "visível" if value else "oculta"
        self.status_bar.showMessage(f"Camada {state_str}.", 2000)

    @layer_transaction
    def flatten_active_group(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        if not layer or not layer.is_group:
            return
        if self._backend_ready(backend) and not backend.flatten_group(act_idx):
            self.status_bar.showMessage("Não foi possível achatar o grupo no motor.", 2500)
            return
        if not lm.flatten_group(act_idx):
            raise RuntimeError("Falha ao atualizar o modelo ao achatar grupo.")
        self._refresh_canvas()
        self.status_bar.showMessage("Grupo achatado com sucesso.", 2000)

    @layer_transaction
    def flatten_entire_image(self) -> None:
        doc, lm, backend, _ = self._active_layer_context()
        if not lm:
            return
        guard = 0
        while any(layer.is_group for layer in lm.layers):
            guard += 1
            if guard > len(lm.layers) + 1:
                raise RuntimeError("Achatar grupos não apresentou progresso.")
            idx = next(i for i, layer in enumerate(lm.layers) if layer.is_group)
            if self._backend_ready(backend) and not backend.flatten_group(idx):
                raise RuntimeError("Falha ao achatar grupo.")
            if not lm.flatten_group(idx):
                raise RuntimeError("Falha ao atualizar o modelo ao achatar grupo.")
        while len(lm.layers) > 1:
            top = lm.layers[-1]
            idx = len(lm.layers) - 1
            # Estes dois casos usavam `showMessage(...) + return`, que sai do
            # laço no meio e deixa a transação COMMITAR uma imagem
            # parcialmente achatada (os `raise` do laço de grupos acima já
            # faziam o certo). Levantar aqui desfaz tudo: "Achatar Imagem"
            # passa a ser tudo-ou-nada, e a mensagem chega ao usuário pelo
            # próprio @layer_transaction.
            if self._backend_ready(backend) and not backend.merge_layer_down(idx):
                raise RuntimeError("Não foi possível achatar a imagem no motor.")
            before_count = len(lm.layers)
            if not lm.merge_down(top.uid) or len(lm.layers) >= before_count:
                raise RuntimeError("A operação de achatar não avançou.")
        self._refresh_canvas()
        self.status_bar.showMessage("Imagem achatada completamente.", 2000)

    @layer_transaction
    def open_layer_properties_dialog(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        doc = self.dm.active_document()
        if not doc or not hasattr(doc, "layer_manager"):
            return
        lm = doc.layer_manager
        act_idx = lm.active_index
        if act_idx < 0:
            return
        layer = lm.layers[act_idx]
        dialog = LayerPropertiesDialog(
            name=getattr(layer, "name", "Camada"),
            opacity=getattr(layer, "opacity", 1.0),
            blend_mode=getattr(layer, "blend_mode", 0),
            is_visible=getattr(layer, "visible", True),
            is_alpha_locked=getattr(layer, "alpha_locked", False),
            is_clipping=getattr(layer, "clipping_mask", False),
            parent=self
        )
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            res = dialog.get_results()
            # Cada lm.set_X() abaixo já sincroniza com o motor via
            # sync_backend_property; o bloco de 6 chamadas diretas a backend.set_X()
            # que existia aqui duplicava incondicionalmente TODAS elas (Achado #2 do
            # panorama de auditoria profunda de camadas — o pior caso encontrado:
            # 6 composições completas do canvas repetidas por clique em "OK").
            lm.set_layer_name(act_idx, res["name"])
            lm.set_layer_opacity(act_idx, res["opacity"])
            lm.set_layer_blend_mode(act_idx, res["blend_mode"])
            lm.set_layer_visibility(act_idx, res["is_visible"])
            lm.set_alpha_lock(act_idx, res["is_alpha_locked"])
            lm.set_clipping_mask(act_idx, res["is_clipping"])
            self._refresh_canvas()
            self.status_bar.showMessage("Propriedades da camada atualizadas.", 2000)

