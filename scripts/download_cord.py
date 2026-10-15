import json
from pathlib import Path
from datasets import load_dataset

ds = load_dataset("naver-clova-ix/cord-v2", split="test")
out = Path("../../data/cord_test")
out.mkdir(exist_ok=True)

for i, row in enumerate(ds):
    row["image"].convert("RGB").save(out / f"receipt_{i:03d}.jpg", quality=95)
    gt = json.loads(row["ground_truth"])
    (out / f"receipt_{i:03d}.json").write_text(json.dumps(gt, indent=2))