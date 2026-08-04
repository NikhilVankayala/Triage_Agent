from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel
from app.db import get_connection

app = FastAPI()

class RequestCreate(BaseModel):
    raw_text: str

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