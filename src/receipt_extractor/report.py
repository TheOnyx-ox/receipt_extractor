import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOP_FIELDS = ["subtotal", "total", "cash", "card", "change", "tax", "service_charge", "discount"]
ITEM_FIELDS = ["name", "unit_price", "quantity", "line_total"]


def load_reports(folder, start, end):
    for path in sorted(folder.glob("receipt_*.json")):
        index = int(path.stem.split("_")[1])
        if start <= index < end:
            yield json.loads(path.read_text())


def field_accuracy(folder, start, end):
    hits = {f: [0, 0] for f in TOP_FIELDS}                      # [correct, total]
    hits.update({f"item.{f}": [0, 0] for f in ITEM_FIELDS})
    count = 0
    for report in load_reports(folder, start, end):
        count += 1
        for f in TOP_FIELDS:
            hits[f][1] += 1
            hits[f][0] += bool(report[f])
        for key, value in report.items():
            if key.startswith("product-"):
                for f in ITEM_FIELDS:
                    hits[f"item.{f}"][1] += 1
                    hits[f"item.{f}"][0] += bool(value[f])
    return count, hits


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "validations"
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9

    count, hits = field_accuracy(folder, start, end)

    lines = [f"Receipts: {count}", "", "| Field | Correct | Total | Accuracy |", "|---|---|---|---|"]
    for field, (correct, total) in hits.items():
        pct = 100 * correct / total if total else 0
        lines.append(f"| {field} | {correct} | {total} | {pct:.1f}% |")
    table = "\n".join(lines)

    print(table)

    out_dir = ROOT / "docs"
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"accuracy_{folder.name}.md").write_text(table + "\n")

if __name__ == "__main__":
    main()