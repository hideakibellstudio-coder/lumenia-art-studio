"""Atualizações pelo Velopack: buscar, baixar o delta e aplicar ao fechar."""

from ui.infrastructure.updater.update_worker import UpdateThread, UpdateWorker
from ui.infrastructure.updater.velopack_updater import FoundUpdate, VelopackUpdater

__all__ = ["FoundUpdate", "UpdateThread", "UpdateWorker", "VelopackUpdater"]
