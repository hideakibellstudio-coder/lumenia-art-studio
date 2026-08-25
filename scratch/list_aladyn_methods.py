import os

p = r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia\ui\engine_backends\aladyn.py"

with open(p, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "def " in line:
            print(f"{i}: {line.strip()}")
