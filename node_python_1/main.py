import sys
import json
import os

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(NODE_DIR, "config.json")
with open(config_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

def process(data):
    return data.get("data")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"code": -1, "error": "no input"}))
        sys.exit(1)

    input_data = json.loads(sys.argv[1])
    result = process(input_data)

    print(json.dumps({
        "code": 0,
        "type": cfg["output_type"],
        "data": result
    }, ensure_ascii=False))