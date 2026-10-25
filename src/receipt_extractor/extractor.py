import base64
import time
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from models import Receipt
import json
import os
from pydantic import ValidationError
from validators import validate, explain

load_dotenv()

client = OpenAI()

PRICE_IN = 0.25
PRICE_OUT = 1.00
PRICE_CACHED_IN = 0.125

ROOT = Path(__file__).resolve().parent.parent.parent
LOG_PATH = ROOT / 'data' / 'logs'


SYSTEM_PROMPT = """You extract structured data from a photo of a receipt.
General:
- Copy values exactly as printed. Never recalculate, correct or "fix" any number, even if the math looks wrong.
- If a field is not on the receipt, return null. Do not guess.
- Include only purchased items in products, not totals, tax or payment lines.

Amounts:
- Write every amount as a plain number with no thousands separators and no currency symbol.
- A "." or "," followed by exactly three digits is a thousands separator: 82,000 and 82.000 both mean 82000; 174.600 means 174600. Never drop those digits.
- Use a dot only for real decimals (12.50). Receipts in Indonesian rupiah (Rp) have no decimals.
- Write discount, tax and service_charge as positive numbers, even if printed with a minus sign.

Fields:
- total is the final amount due after tax and service charge (TOTAL, GRAND TOTAL, AMOUNT DUE). It is not the cash handed over.
- Put cash given in cash, a card payment in card, and money returned in change.
- subtotal is the sum before tax, only if printed. tax, service_charge and discount are the printed amounts, not percentages.
- currency is the ISO code if a symbol or code is printed (Rp -> IDR), otherwise null.

Products:
- name as printed, quantity (1 if not shown).
- The price printed at the end of an item line is its line_total. Set unit_price only if a per-unit price is printed; otherwise null. Never multiply by quantity.
"""


def construct_request(image: Path, feedback: str | None = None):
    b64 = base64.b64encode(image.read_bytes()).decode()
    content = [
        {"type": "input_text", "text": "Extract the receipt data."},
        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
    ]
    if feedback:
        content.append({"type": "input_text", "text": feedback})
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def send_receipt(image: Path, feedback: str | None = None):
    request = construct_request(image, feedback)
    return client.responses.parse(
        model="gpt-4o-mini",
        input=request,
        text_format=Receipt,
    )


def extract_receipt(image: Path, save_to: Path, feedback: str | None = None):
    start_time = time.perf_counter()
    result = send_receipt(image, feedback)
    end_time = time.perf_counter()

    if result.output_parsed is None:
        raise ValueError(f"Model returned no parsed output for {image.name}")

    os.makedirs(save_to, exist_ok=True)
    os.makedirs(LOG_PATH, exist_ok=True)

    (save_to / f"{image.stem}.json").write_text(result.output_parsed.model_dump_json(indent=2))

    usage = result.usage
    cached = usage.input_tokens_details.cached_tokens
    entry = {
        "receipt": image.stem,
        "attempt": 2 if feedback else 1,
        "model": "gpt-4o-mini",
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "latency_sec": round(end_time - start_time, 2),
        "cost_usd": ((usage.input_tokens - cached) * PRICE_IN
                     + cached * PRICE_CACHED_IN
                     + usage.output_tokens * PRICE_OUT) / 1_000_000,
    }
    with open(LOG_PATH / "calls.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    return result.output_parsed


def extract_with_retry(image: Path, first_dir: Path, retry_dir: Path):
    record = {"receipt": image.stem, "retried": False}
    first, problems = None, None

    try:
        first = extract_receipt(image, first_dir)
        issues = validate(first)["issues"]
        record["issues_before"] = issues
        if issues:
            problems = ("Your previous answer was:\n" + first.model_dump_json() + "\nIt failed these checks:\n" + explain(first, issues))
    except (ValidationError, ValueError) as e:
        record["issues_before"] = ["parse_error"]
        problems = f"Your previous answer could not be parsed:\n{e}"

    final = first
    if problems:
        record["retried"] = True
        feedback = (problems + "\nLook at the receipt again and correct only the values you misread. If the receipt itself does not add up, keep the printed values.")
        try:
            second = extract_receipt(image, retry_dir, feedback)
            issues_after = validate(second)["issues"]
            record["issues_after"] = issues_after
            record["fixed"] = not issues_after
            if first is None or len(issues_after) < len(record["issues_before"]):
                final = second
        except (ValidationError, ValueError):
            record["issues_after"] = ["parse_error"]
            record["fixed"] = False

    os.makedirs(LOG_PATH, exist_ok=True)
    with open(LOG_PATH / "retries.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")
    return final, record