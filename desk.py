"""Small ticket desk used only as the test application's own target."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Doorlist")


@contextmanager
def connection():
    db = sqlite3.connect(os.environ.get("DOORLIST_DB","desk.db"),timeout=15)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS shows(id TEXT PRIMARY KEY, capacity INTEGER NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS tickets(
            show TEXT, request_id TEXT, qty INTEGER, cancelled INTEGER DEFAULT 0,
            PRIMARY KEY(show,request_id))""")
        with db:
            yield db
    finally:
        db.close()


class Venue(BaseModel):
    capacity: int = Field(ge=1,le=500)


class Order(BaseModel):
    request_id: UUID
    qty: int = Field(ge=1,le=6)


def remaining(db, show):
    r = db.execute("""SELECT capacity - COALESCE((SELECT SUM(qty) FROM tickets
        WHERE show=shows.id AND cancelled=0),0) FROM shows WHERE id=?""",(show,)).fetchone()
    if r is None:
        raise HTTPException(404,"Show not found")
    return r[0]


@app.post("/shows", status_code=201)
def create(data: Venue):
    show=str(uuid4())
    with connection() as db:
        db.execute("INSERT INTO shows VALUES(?,?)",(show,data.capacity))
    return {"id":show}


@app.get("/shows/{show}")
def status(show: UUID):
    with connection() as db:
        return {"remaining":remaining(db,str(show))}


@app.post("/shows/{show}/tickets")
def book(show: UUID, order: Order):
    show, key = str(show), str(order.request_id)
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        left = remaining(db,show)
        existing = db.execute("SELECT qty,cancelled FROM tickets WHERE show=? AND request_id=?",(show,key)).fetchone()
        if existing:
            if existing != (order.qty,0):
                raise HTTPException(409,"Request ID already used")
        else:
            if order.qty > left:
                raise HTTPException(409,"Insufficient tickets")
            db.execute("INSERT INTO tickets(show,request_id,qty) VALUES(?,?,?)",(show,key,order.qty))
        return {"id":key,"remaining":remaining(db,show)}


@app.delete("/shows/{show}/tickets/{ticket}")
def cancel(show: UUID, ticket: UUID):
    with connection() as db:
        cur = db.execute("UPDATE tickets SET cancelled=1 WHERE show=? AND request_id=?",(str(show),str(ticket)))
        if cur.rowcount != 1:
            raise HTTPException(404,"Ticket not found")
        return {"remaining":remaining(db,str(show))}


@app.get("/", response_class=HTMLResponse)
def home():
    return Path(__file__).with_name("desk.html").read_text(encoding="utf-8")
