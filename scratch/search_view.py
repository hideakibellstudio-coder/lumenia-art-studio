import os

p = r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia\plugins\system\workspace_core\workspace\canvas\render_widget.py"

with open(p, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "update_view" in line or "set_view" in line or "camera" in line.lower():
            print(f"{i}: {line.strip()}")
