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

def construct_request(image: Path):
    b64 = base64.b64encode(open(image, "rb").read()).decode()
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who needs to extract information from the provided receipt"

        },
        {
        "role": "user",
        "content": [
            {"type": "input_image",
            "image_url": f"data:image/jpeg;base64,{b64}"} ,
        ]
    }]

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



