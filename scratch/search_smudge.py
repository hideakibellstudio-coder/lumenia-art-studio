import os
import sys

keywords = ["smudge", "blur"]
search_dirs = [
    r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia",
    r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE"
]

results = []
for sdir in search_dirs:
    for root, dirs, files in os.walk(sdir):
        if "build" in root or ".git" in root or "__pycache__" in root or "scratch" in root:
            continue
        for f in files:
            if f.endswith((".py", ".cpp", ".h", ".hpp", ".json")):
                p = os.path.join(root, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                        for i, line in enumerate(fp, 1):
                            l_lower = line.lower()
                            if any(k in l_lower for k in keywords):
                                results.append(f"{p}:{i}: {line.strip()[:100]}")
                except Exception as e:
                    pass

with open("scratch/smudge_search_results.txt", "w", encoding="utf-8") as out:
    for r in results:
        out.write(r + "\n")
    out.write(f"\nTotal occurrences: {len(results)}\n")

print(f"Wrote {len(results)} occurrences to scratch/smudge_search_results.txt")
