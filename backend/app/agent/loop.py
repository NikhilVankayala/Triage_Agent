import json
from anthropic import Anthropic
from dotenv import load_dotenv
import re

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
