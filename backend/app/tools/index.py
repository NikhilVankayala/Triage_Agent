from app.db import get_connection
from psycopg.rows import dict_row
import json


def lookup_order(order_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT customer_name, product, amount_cents FROM orders WHERE id = %s", (order_id,),)
            row = cur.fetchone()
    if row is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, **row}

def propose_action(request_id: int, tool_name: str, arguments: dict) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO proposed_actions (request_id, tool_name, arguments) "
                "VALUES (%s, %s, %s) "
                "RETURNING id, request_id, tool_name, arguments, status",
                (request_id, tool_name, json.dumps(arguments)),
            )
            row = cur.fetchone()
            conn.commit()
    return dict(row)

def execute_action(tool_name: str, arguments: dict) -> dict:
    if tool_name == "issue_refund":
        return {
            "executed": True,
            "detail": f"Refunded {arguments['amount_cents']} cents for order {arguments['order_id']}",
        }
    elif tool_name == "create_ticket":
        return {
            "executed": True,
            "detail": f"Opened ticket (priority {arguments['priority']}): {arguments['summary']}",
        }
    elif tool_name == "send_reply":
        return {
            "executed": True,
            "detail": "Reply sent to customer",
        }
    else:
        return {"executed": False, "detail": f"Unknown tool: {tool_name}"}

def resolve_action(proposed_action_id: int, decision: str) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM proposed_actions WHERE id = %s", (proposed_action_id,))
            proposed_action = cur.fetchone()

            if proposed_action is None:
                return {"error": "Proposed action doesn't exist"}

            if proposed_action["status"] != "pending":
                return {"error": f"Action already resolved (status: {proposed_action['status']})"}

            if decision == "reject":
                cur.execute(
                    "UPDATE proposed_actions SET status = %s WHERE id = %s "
                    "RETURNING id, tool_name, status, result",
                    ("rejected", proposed_action_id),
                )
            elif decision == "approve":
                result = execute_action(proposed_action["tool_name"], proposed_action["arguments"])
                cur.execute(
                    "UPDATE proposed_actions SET status = %s, result = %s WHERE id = %s "
                    "RETURNING id, tool_name, status, result",
                    ("executed", json.dumps(result), proposed_action_id),
                )
            else:
                return {"error": f"Invalid decision: {decision}"}

            updated_row = cur.fetchone()
            conn.commit()

    return dict(updated_row)

def store_classification(request_id: int, category: str, urgency: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE requests SET category = %s, urgency = %s WHERE id = %s",
                (category, urgency, request_id),
            )
            conn.commit()

def store_extracted_fields(request_id: int, fields: dict) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO extracted_fields (request_id, fields) VALUES (%s, %s)",
                (request_id, json.dumps(fields)),
            )
            conn.commit()