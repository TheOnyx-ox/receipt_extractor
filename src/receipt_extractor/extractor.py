import base64
import time
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from models import Receipt
import json
import os
import pandas as pd

load_dotenv()

client = OpenAI()

PRICE_IN = 0.25
PRICE_OUT = 1.00
PRICE_CACHED_IN = 0.125

ROOT = Path(__file__).resolve().parent.parent.parent
LOG_PATH = ROOT / 'data' / 'logs'

SYSTEM_PROMPT = """You extract structured data from a photo of a receipt.
Rules:
- Copy values exactly as printed. Never recalculate, correct or "fix" any number, even if the math looks wrong.
- Write every amount as a plain number with no thousands separators and no currency symbol (for example 43636, not "43.636" or "43,636"). Use a dot only for real decimals (12.50).
- total is the final amount due after tax and service charge (labels like TOTAL, GRAND TOTAL, AMOUNT DUE). It is not the cash handed over. Put the cash given in cash, a card payment in card, and the money returned in change.
- subtotal is the sum before tax, only if printed. tax, service_charge and discount are the printed amounts, not percentages.
- For each product: name as printed, unit_price (price of one unit), quantity (default 1 if not shown), line_total (price for that line).
- If a field is not on the receipt, return null. Do not guess or infer it.
- Include only purchased items in products, not totals, tax or payment lines.
"""


def construct_request(image: Path):
    b64 = base64.b64encode(image.read_bytes()).decode()
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Extract the receipt data."},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
            ],
        },
    ]

def send_receipt(image: Path):
    request = construct_request(image)
    result = client.responses.parse(
        model = "gpt-4o-mini",
        input=request,
        text_format=Receipt
    )

    return result

def extract_receipt(image: Path, save_to: Path):
    start_time = time.perf_counter()
    result = send_receipt(image)
    end_time = time.perf_counter()

    os.makedirs(f"{save_to}", exist_ok=True)
    os.makedirs(f"{LOG_PATH}", exist_ok=True)

    Path(save_to.resolve() / f"{image.stem}.json").write_text(result.output_parsed.model_dump_json(indent=2))

    entry = {
        "receipt" : image.stem,
        'model': 'gpt-4o-mini',
        "input_tokens": result.usage.input_tokens,
        "output_tokens": result.usage.output_tokens,
        "total_tokens": result.usage.total_tokens,
        "latency_sec" : round(end_time - start_time, 2),
        'cost_usd': (result.usage.input_tokens * PRICE_IN + result.usage.output_tokens * PRICE_OUT + result.usage.input_tokens_details.cached_tokens * PRICE_CACHED_IN) / 1_000_000

    }
    with open(LOG_PATH / f'calls.jsonl', 'a') as f:
        f.write(json.dumps(entry) + '\n')
    return result.output_parsed



