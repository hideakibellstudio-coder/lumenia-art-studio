"""Estado efetivo dos atalhos, compartilhado pelos comandos locais do canvas."""

from __future__ import annotations

from PySide6 import QtGui

from ui.core.shortcut_catalog import DEFAULT_SHORTCUTS


class ShortcutBindings:
    """Converte o mapa validado em combinações Qt consultáveis sem UI global."""

    _effective = {item["id"]: item["default"] for item in DEFAULT_SHORTCUTS}
    _commands_by_combined: dict[int, str] = {}

    @classmethod
    def configure(cls, effective: dict[str, str]) -> None:
        cls._effective = dict(effective)
        cls._commands_by_combined = {}
        for command, sequence in cls._effective.items():
            key_sequence = QtGui.QKeySequence(sequence)
            if key_sequence.count() == 1 and not key_sequence.isEmpty():
                cls._commands_by_combined[key_sequence[0].toCombined()] = command

    @classmethod
    def command_for_event(cls, event: QtGui.QKeyEvent) -> str | None:
        return cls._commands_by_combined.get(event.keyCombination().toCombined())

    @classmethod
    def matches(cls, command: str, event: QtGui.QKeyEvent) -> bool:
        return cls.command_for_event(event) == command


ShortcutBindings.configure(ShortcutBindings._effective)
