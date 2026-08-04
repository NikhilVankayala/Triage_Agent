from app.db import get_connection
from psycopg.rows import dict_row


def lookup_order(order_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT customer_name, product, amount_cents FROM orders WHERE id = %s", (order_id,),)
            row = cur.fetchone()
    if row is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, **row}
