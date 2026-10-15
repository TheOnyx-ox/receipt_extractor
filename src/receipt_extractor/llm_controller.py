from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
#
# b64 = base64.b64encode(open("receipt_000.jpg", "rb").read()).decode()
#
# {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},


