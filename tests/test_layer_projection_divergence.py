"""Deteccao de ordem divergente entre Document e motor (Achado #5).

Cobre o guard que DocumentHistory.bind_projection_identities executa antes de
vincular identidades por posicao. A vinculacao por posicao e necessaria (uma
camada recem-criada nasce com uid 0 no motor, e um clone nativo herda o uid da
origem), mas apaga a evidencia do unico tipo de divergencia que os guards de
contagem, tipo e hierarquia nao pegam: mesma populacao de camadas em ordem
diferente. O guard registra esse caso em log sem interromper a acao do usuario.

Os dubles aqui sao propositais: o objetivo e fixar a fronteira entre "isto e
divergencia real" e "isto e uma operacao normal", sem depender do motor nativo.
"""
import logging
import unittest

from ui.core.document.history import DocumentHistory


class FakeBackend:
    def __init__(self, native_uids):
        self.native_uids = list(native_uids)

    def get_drawing_layer_count(self):
        return len(self.native_uids)

    def get_layer_info(self, index):
        return {"document_uid": self.native_uids[index]}

    def set_layer_document_uid(self, index, uid):
        self.native_uids[index] = uid
        return True


class FakeBackendWithoutLayerInfo:
    """Duble antigo, sem get_layer_info: o guard precisa simplesmente sair."""

    def __init__(self, count):
        self.count = count
        self.bound = []

    def get_drawing_layer_count(self):
        return self.count

    def set_layer_document_uid(self, index, uid):
        self.bound.append((index, uid))
        return True


class FakeLayer:
    def __init__(self, uid):
        self.uid = uid


class FakeDocument:
    uid = "doc-projecao"

    def __init__(self, model_uids):
        self.layer_manager = type("M", (), {"layers": [FakeLayer(u) for u in model_uids]})()


class TestLayerOrderDivergence(unittest.TestCase):
    def _bind(self, native_uids, model_uids, backend=None):
        history = DocumentHistory(FakeDocument(model_uids))
        backend = backend or FakeBackend(native_uids)
        with self.assertLogs("ui.core.document.history", level=logging.ERROR) as captured:
            logging.getLogger("ui.core.document.history").error("sentinela")
            history.bind_projection_identities(backend)
        return backend, [line for line in captured.output if "sentinela" not in line]

    def test_estado_consistente_nao_registra(self):
        _, logs = self._bind([10, 11, 12], [10, 11, 12])
        self.assertEqual(logs, [])

    def test_camada_nova_com_uid_zero_nao_registra(self):
        _, logs = self._bind([10, 0, 12], [10, 13, 12])
        self.assertEqual(logs, [])

    def test_clone_que_herda_uid_da_origem_nao_registra(self):
        # LayerStack.cpp::cloneLayer copia o documentUid, entao logo apos um
        # duplicate o motor tem o mesmo uid em dois indices.
        _, logs = self._bind([10, 10, 12], [10, 13, 12])
        self.assertEqual(logs, [])

    def test_populacoes_diferentes_nao_registram(self):
        _, logs = self._bind([10, 12], [10, 11])
        self.assertEqual(logs, [])

    def test_bootstrap_com_motor_zerado_nao_registra(self):
        _, logs = self._bind([0, 0, 0], [10, 11, 12])
        self.assertEqual(logs, [])

    def test_mesma_populacao_em_ordem_diferente_registra(self):
        _, logs = self._bind([11, 10, 12], [10, 11, 12])
        self.assertEqual(len(logs), 1)
        self.assertIn("ordem de camadas divergente", logs[0])

    def test_rotacao_tambem_registra(self):
        _, logs = self._bind([12, 10, 11], [10, 11, 12])
        self.assertEqual(len(logs), 1)

    def test_vinculacao_por_posicao_continua_acontecendo(self):
        backend, _ = self._bind([11, 10, 12], [10, 11, 12])
        self.assertEqual(backend.native_uids, [10, 11, 12])

    def test_backend_sem_get_layer_info_segue_vinculando(self):
        backend = FakeBackendWithoutLayerInfo(2)
        backend, logs = self._bind([], [10, 11], backend=backend)
        self.assertEqual(logs, [])
        self.assertEqual(backend.bound, [(0, 10), (1, 11)])

    def test_pilhas_de_tamanhos_diferentes_continuam_levantando(self):
        history = DocumentHistory(FakeDocument([10, 11]))
        with self.assertRaises(RuntimeError):
            history.bind_projection_identities(FakeBackend([10]))


if __name__ == "__main__":
    unittest.main()
