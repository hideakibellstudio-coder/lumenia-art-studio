import os

keywords = ["wheelevent", "gesture", "zoom", "pinch", "nativegesture"]
search_dirs = [
    r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia UI",
    r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia"
]

results = []
for sdir in search_dirs:
    for root, dirs, files in os.walk(sdir):
        if "build" in root or ".git" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith((".py", ".cpp", ".h")):
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                        for i, line in enumerate(fp, 1):
                            l_lower = line.lower()
                            if any(k in l_lower for k in keywords) and ("wheelevent" in l_lower or "gesture" in l_lower or "pinch" in l_lower):
                                results.append(f"{p}:{i}: {line.strip()[:100]}")
                except Exception:
                    pass

for r in results[:40]:
    print(r)
