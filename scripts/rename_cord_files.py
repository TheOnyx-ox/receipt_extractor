from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "cord_test"
EXTS = {".jpg", ".json"}
DRY_RUN = False

groups = defaultdict(list)
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.suffix.lower() in EXTS:
        groups[p.stem].append(p)

for stem, files in groups.items():
    if {p.suffix.lower() for p in files} != EXTS:
        print(f"WARNING: {stem} is missing its .jpg or .json partner")

plan = []
for i, stem in enumerate(sorted(groups)):
    for src in groups[stem]:
        dst = src.with_name(f"receipt_{i:03d}{src.suffix.lower()}")
        if src != dst:
            plan.append((src, dst))

for src, dst in plan:
    print(f"{src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")

if not DRY_RUN:
    temp = []
    for src, dst in plan:
        tmp = src.with_name(src.name + ".tmp")
        src.rename(tmp)
        temp.append((tmp, dst))
    for tmp, dst in temp:
        tmp.rename(dst)
    print(f"Renamed {len(plan)} files")