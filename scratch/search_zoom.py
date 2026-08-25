import os

keywords = ["clamp", "zoom", "pinch", "wheel", "gesture", "nativegesture"]
p = r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia\plugins\system\workspace_core\workspace\canvas\render_widget.py"

with open(p, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if any(k in line.lower() for k in keywords):
            print(f"{i}: {line.strip()[:100]}")
