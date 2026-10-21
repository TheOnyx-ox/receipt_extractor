import ast
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "logs"
with open(ROOT/'calls.jsonl', 'r') as f:
    data = f.readlines()


avg_input_tokens = avg_output_tokens = avg_latency = avg_cost_per_call = total_cost = total_latency = total_tokens = 0

num_calls = len(data)

for line in data:
    line = ast.literal_eval(line)
    avg_input_tokens += line.get("input_tokens")
    avg_output_tokens += line.get("output_tokens")
    total_latency += line.get("latency_sec")
    total_cost += line.get("cost_usd")


total_tokens = avg_input_tokens + avg_output_tokens

avg_input_tokens = avg_input_tokens / num_calls
avg_output_tokens = avg_output_tokens / num_calls

avg_latency = total_latency / num_calls
avg_cost_per_call = total_cost / num_calls

sum_data = {
    "num_calls": num_calls,
    "avg_input_tokens": avg_input_tokens,
    "avg_output_tokens": avg_output_tokens,
    "avg_latency": avg_latency,
    "avg_cost_per_call": avg_cost_per_call,
    "total_tokens": total_tokens,
    "total_latency": total_latency,
    "total_cost": total_cost,
}

with open(ROOT/'sum_calls.json', 'w') as f:
    f.write(json.dumps(sum_data))
