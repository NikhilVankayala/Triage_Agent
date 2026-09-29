from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel
from app.db import get_connection
from app.tools.index import resolve_action, store_classification, store_extracted_fields
from app.agent.loop import plan, classify, extract_fields, generate_reply

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestCreate(BaseModel):
    raw_text: str

class ResolveBody(BaseModel):
    decision: str   # "approve" or "reject"

@app.get("/")
def read_root():
    return {"message": "Triage Agent API is running"}

@app.get("/requests")
def list_requests():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, raw_text, status, created_at FROM requests ORDER BY created_at DESC")
            rows = cur.fetchall()
    return {"requests": rows}

@app.get("/requests/{request_id}")
def get_request(request_id : int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, raw_text, status, created_at FROM requests WHERE id = %s", (request_id,),)
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code = 404, detail="Request not found")

    return {"request": row}


@app.post("/requests")
def create_request(body: RequestCreate):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "INSERT INTO requests (raw_text) VALUES (%s) RETURNING id, raw_text, status, created_at",
                (body.raw_text,)
            )
            row = cur.fetchone()
            conn.commit()
    return {"request": row}

@app.post("/actions/{action_id}/resolve")
def resolve(action_id: int, body: ResolveBody):
    result = resolve_action(action_id, body.decision)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/requests/{request_id}/actions")
def list_actions(request_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, tool_name, arguments, status, result, created_at "
                "FROM proposed_actions WHERE request_id = %s "
                "ORDER BY id",
                (request_id,),
            )
            rows = cur.fetchall()
    return {"actions": rows}

@app.post("/requests/{request_id}/triage")
def triage(request_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, raw_text FROM requests WHERE id = %s", (request_id,))
            request = cur.fetchone()

    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    raw_text = request["raw_text"]

    # full pipeline: classify -> extract -> plan
    classification = classify(raw_text)
    store_classification(request_id, classification["category"], classification["urgency"])

    fields = extract_fields(raw_text)
    store_extracted_fields(request_id, fields)

    plan(request_id, raw_text)

    return {"request_id": request_id, "classification": classification, "extracted": fields, "message": "Triage complete"}

@app.post("/requests/{request_id}/finalize")
def finalize(request_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, raw_text FROM requests WHERE id = %s", (request_id,))
            request = cur.fetchone()
            if request is None:
                raise HTTPException(status_code=404, detail="Request not found")

            cur.execute(
                "SELECT tool_name, arguments, status, result FROM proposed_actions "
                "WHERE request_id = %s AND status IN ('executed', 'rejected') "
                "ORDER BY id",
                (request_id,),
            )
            resolved = cur.fetchall()

    reply = generate_reply(request["raw_text"], resolved)
    return {"request_id": request_id, "reply": reply}