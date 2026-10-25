# Receipt Extractor

A photo of a receipt goes in, validated JSON comes out.

A vision model reads the receipt into a typed schema, plain-code validators check that the numbers add up, and if they don't, the model gets **one** retry with the exact error message. The project also measures how well it works: per-field accuracy against ground truth, with and without the retry, plus tokens, cost and latency for every call.

Built with the Python 3.14, Pydantic, Typer and pytest.

## How it works

```
receipt photo
     |
     v
vision model (gpt-4o-mini, structured output -> Receipt schema)
     |
     v
validators (plain code)
  - line items sum to subtotal
  - subtotal + tax + service charge - discount = total
  - unit price x quantity = line total
  - cash - total = change
     |
     |-- all pass --------------------------> JSON
     |
     '-- something fails --> retry once with the error message --> re-validate --> JSON + issues
```

Design decisions:

- **Wrong math is flagged, never fixed.** The prompt tells the model to copy printed values exactly, and the validators only report. If a receipt really doesn't add up, the output says so instead of silently "correcting" it.
- **Missing is not wrong.** A rule whose fields are absent is skipped, not failed.
- **Number formats.** Receipts in the CORD dataset use `.` and `,` as thousands separators (Indonesian rupiah, no decimals), while other receipts use them as decimal marks. One shared `parse_amount` rule (a separator followed by exactly three digits is a thousands separator) normalises `43.636`, `3,000`, `1.234,56` and `1,234.56`. It runs inside the Pydantic model, so it applies to the model's output and to the ground-truth labels alike.
- **Every call is logged** (tokens, cost, latency, attempt number) to JSONL, and every retry decision is logged too.

## Setup

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env      # then put your OPENAI_API_KEY in .env
```

## Usage

Extract one receipt and print the validated result:

```bash
uv run python src/receipt_extractor/cli.py examples/receipt_002.jpg
```

The output contains the extracted receipt, the validator results (`true` / `false` / `null` for skipped), and whether a retry was needed.

Run the tests (no API key needed):

```bash
uv run pytest
```

## Evaluation

The evaluation uses receipts from the test split of [CORD-v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2) (real photos with labels). The data is not stored in this repo. To rebuild it, run the scripts in `scripts/`:

1. `download_cord.py` downloads the receipts
2. `convert_cord_labels.py` turns CORD labels into this project's `Receipt` format
3. `rename_cord_files.py` renames files to `receipt_NNN`

Then, from `src/receipt_extractor`:

```bash
uv run python evaluate.py                                        # extract, validate, retry, score
uv run python report.py ../../data/validations_first 0 22        # table without retry
uv run python report.py ../../data/validations_final 0 22        # table with retry
```

Scoring compares each prediction with the ground truth. Items are matched one-to-one by name similarity, and each field is correct or not. Two empty values count as a match.

## Results

22 receipts. These were also used while tuning the prompt, so treat this as a **development set**, not a held-out test. With only 22 receipts, one field on one receipt moves a percentage by several points.

Average accuracy per receipt: **80.3% without retry, 82.1% with retry.**

| Field | Without retry | With retry |
|---|---|---|
| subtotal | 68.2% | 72.7% |
| total | 81.8% | 86.4% |
| cash | 95.5% | 95.5% |
| card | 100.0% | 100.0% |
| change | 90.9% | 95.5% |
| tax | 81.8% | 81.8% |
| service_charge | 95.5% | 95.5% |
| discount | 95.5% | 95.5% |
| item name | 96.4% | 96.4% |
| item unit_price | 39.3% | 41.1% |
| item quantity | 92.9% | 92.9% |
| item line_total | 80.4% | 82.1% |

Full tables: [`docs/accuracy_validations_first.md`](docs/accuracy_validations_first.md) and [`docs/accuracy_validations_final.md`](docs/accuracy_validations_final.md). Per-receipt reports are in [`results/`](results/).

What the numbers say:

- **Reading what was bought works well:** names 96%, quantities 93%.
- **The weak spot is digits on low-quality photos.** Subtotal and line totals are the lowest amount fields, even after the retry. The photos are often dark, crumpled or blurry (for example, in `receipt_002` a `61,000` was misread as `67,000` in several runs).
- **The retry helps a little and only where a validator can see the problem.** It fixed wrong `total`, `subtotal`, `change` and `line_total` values on a few receipts. It cannot fix a misread that stays arithmetically consistent, and it cannot help with `tax`, which no validator checks.
- **`unit_price` (about 40%) is a labelling mismatch more than a model error.** The prompt asks for `null` unless a per-unit price is printed, while the CORD labels often include one.
- **`card`, `tax`, `service_charge` and `discount` are mostly empty** in both prediction and ground truth, and two empty values count as correct, so those rows look better than they are.

### Validators on the ground truth

Running the same validators on the ground-truth labels, 21 of 22 pass every rule. So the rules fit this data, and the failures in the predictions are mostly the model's errors, not rule noise.

### Retry rate

TODO: fill from `data/logs/retries.jsonl` - N receipts, X retried, Y fixed.

### Cost and latency

TODO: fill from `results/sum_calls.json` - average cost per receipt (including retries), average latency per call, total tokens.

## Limitations

- **Small development set.** 22 receipts, all used while tuning the prompt. A larger held-out run is a one-line change in `evaluate.py` (`LIMIT`) and costs about a dollar for 100 receipts.
- **Photos only.** CORD contains only photos, so there is no clean-scan versus photo comparison, and PDFs are not handled.
- **One model.** All numbers are for `gpt-4o-mini`. The misread digits may be a vision limit; a stronger model for only the flagged receipts is an obvious next experiment.
- **Some validators are silent.** Tax is not checked against a printed percentage, and a consistent scale error (every amount off by 1000) would pass all arithmetic rules. Only the comparison with ground truth catches that.
- **Failed parses are not logged.** If a model answer fails Pydantic validation inside the SDK call, the call is billed but has no usage entry, so the cost totals slightly understate the real cost.

## Project layout

```
src/receipt_extractor/
  models.py      Pydantic schema (Receipt, Item) and amount parsing
  extractor.py   OpenAI call, logging, retry with validator feedback
  validators.py  arithmetic checks and error explanations
  evaluate.py    scoring against ground truth
  report.py      per-field accuracy tables
  cli.py         Typer command-line interface
scripts/         dataset download, label conversion, renaming, log summary
tests/           pytest tests for amount parsing and validators
examples/        a few receipts with ground truth, prediction and retry output
results/         per-receipt score reports and cost summary
docs/            accuracy tables
```

## Data

Receipt images and labels come from CORD-v2 (Naver Clova). See the [dataset page](https://huggingface.co/datasets/naver-clova-ix/cord-v2) for license and attribution terms.