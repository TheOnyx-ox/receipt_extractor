import base64
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from models import Receipt
import json
import os

load_dotenv()

client = OpenAI()

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


path = Path("cord_test/receipt_002.jpg")
result = send_receipt(path)

SAVE_DIR = "receipt_outputs_json"

os.makedirs(f"{SAVE_DIR}", exist_ok=True)

Path(SAVE_DIR + "/" + f"{path.stem}.json").write_text(result.output_parsed.model_dump_json(indent=2))



