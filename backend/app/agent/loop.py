import json
from anthropic import Anthropic
from dotenv import load_dotenv
import re
from app.tools.index import lookup_order

load_dotenv()

client = Anthropic()

CHEAP_MODEL = "claude-haiku-4-5"
REASONING_MODEL = "claude-sonnet-5"

def classify(raw_text: str) -> dict:
    response = client.messages.create(
        model=CHEAP_MODEL,
        max_tokens=200,
        system=(
            "Classify the support message. Respond with ONLY a JSON object, no other text: "
            '{"category": "complaint|billing|general", '
            '"urgency": "low|medium|high", '
            '"actionable": true|false}'
        ),

        messages = [
            {"role": "user", "content": raw_text}
        ],
    )

    text = response.content[0].text
    return extract_json(text)


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text}")
    return json.loads(match.group(0))

def extract_fields(raw_text: str) -> dict:
    response = client.messages.create(
        model=REASONING_MODEL,
        max_tokens=500,
        system=("Extract structured fields from the support message. "
        "Respond with ONLY a JSON object, no other text: "
        '{"customer_name": string or null, '
        '"order_id": number or null, '
        '"issue": string, '
        '"requested_action": string}. '
        "Use null for order_id or customer_name if not present in the message."
        ),
        messages=[{"role":"user", "content":raw_text}]
    )

    text = response.content[0].text

    return extract_json(text)

LOOKUP_ORDER_TOOL = {
    "name": "lookup_order",
    "description": "Look up an order by its numeric ID to check it exists and get customer, product, and amount. Call this to verify an order before proposing a refund.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "number", "description": "The numeric order ID"}
        },
        "required": ["order_id"],
    },
}

def plan(raw_text: str):
    messages = [{"role": "user", "content": raw_text}]

    for turn in range(5):
        response = client.messages.create(
            model=REASONING_MODEL,
            max_tokens=1000,
            tools=[LOOKUP_ORDER_TOOL],
            messages=messages
        )

        if response.stop_reason != "tool_use":
            #Claude is done
            print("Final stop reason", response.stop_reason)
            for block in response.content:
                if block.type == "text":
                    print("claude says", block.text)
            return response

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                print("claude calls", block.name, "with", block.input)

                if block.name == "lookup_order":
                    result = lookup_order(block.input["order_id"])
                else:
                    result = {"error": f"Unknown tool: {block.name}"}
                print(f"result: {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                })

        messages.append({"role": "user", "content": tool_results})
        
    print("Hit turn limit")
    return None

