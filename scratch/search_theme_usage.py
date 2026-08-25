import os

keywords = ["dark_default", "lumenia_purple"]
search_dirs = [
    r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia"
]

for sdir in search_dirs:
    for root, dirs, files in os.walk(sdir):
        if "build" in root or ".git" in root or "__pycache__" in root or "scratch" in root:
            continue
        for f in files:
            if f.endswith((".py", ".json")):
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                        for i, line in enumerate(fp, 1):
                            if any(k in line for k in keywords):
                                print(f"{p}:{i}: {line.strip()}")
                except Exception:
                    pass
