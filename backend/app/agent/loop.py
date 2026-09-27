import json
from anthropic import Anthropic
from dotenv import load_dotenv
import re
from app.tools.index import lookup_order, propose_action   # add propose_action to the import

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

ISSUE_REFUND_TOOL = {
    "name": "issue_refund",
    "description": "Issue a refund for an order. Use when a customer is owed money back for a damaged, defective, or wrongly-charged order. Verify the order exists with lookup_order first.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "number", "description": "The order to refund"},
            "amount_cents": {"type": "number", "description": "Refund amount in cents"},
            "reason": {"type": "string", "description": "Why the refund is being issued"},
        },
        "required": ["order_id", "amount_cents", "reason"],
    },
}

CREATE_TICKET_TOOL = {
    "name": "create_ticket",
    "description": "Open a support ticket for a human team to follow up on. Use when an issue needs human investigation or can't be resolved by an automated action alone.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "number", "description": "The related order, if the ticket concerns a specific order"},
            "summary": {"type": "string", "description": "A short description of what the ticket is about"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How urgent the ticket is",
            },
        },
        "required": ["summary", "priority"],
    },
}

SEND_REPLY_TOOL = {
    "name": "send_reply",
    "description": "Draft a reply to send back to the customer. Use to acknowledge, ask for more information, or explain what is being done.",
    "input_schema": {
        "type": "object",
        "properties": {
            "draft": {"type": "string", "description": "The message text to send to the customer"},
        },
        "required": ["draft"],
    },
}

WRITE_TOOLS = {"issue_refund", "create_ticket", "send_reply"}


def plan(request_id: int, raw_text: str):          # now takes request_id
    messages = [{"role": "user", "content": raw_text}]

    for turn in range(5):
        response = client.messages.create(
            model=REASONING_MODEL,
            max_tokens=1000,
            tools=[LOOKUP_ORDER_TOOL, ISSUE_REFUND_TOOL, CREATE_TICKET_TOOL, SEND_REPLY_TOOL],  # all four tools
            messages=messages,
        )

        if response.stop_reason != "tool_use":
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
                elif block.name in WRITE_TOOLS:
                    proposed = propose_action(request_id, block.name, block.input)
                    result = {
                        "status": "proposed",
                        "message": f"Action '{block.name}' has been proposed and is awaiting human approval. Do not assume it has been executed.",
                        "proposed_action_id": proposed["id"],
                    }
                else:
                    result = {"error": f"Unknown tool: {block.name}"}

                print(f"result: {result}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "user", "content": tool_results})

    print("Hit turn limit")
    return None

