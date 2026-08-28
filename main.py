"""Lumenia Root Entrypoint — Seamlessly delegates to ui.main."""
import sys
import os

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    import ui.main
