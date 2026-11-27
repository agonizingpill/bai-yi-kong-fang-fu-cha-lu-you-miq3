from fastapi import HTTPException
from sqlalchemy import select

def need(condition, explanation):
    if not condition:
        raise HTTPException(409, detail=explanation)

def get(conn, table, key, lock=False):
    pk = table.primary_key.columns.values()[0]
    query = select(table).where(pk == key)
    if lock:
        query = query.with_for_update()
    row = conn.execute(query).mappings().first()
    if row is None:
        raise HTTPException(404, detail=f'找不到 {key}')
    return dict(row)

def scan(conn, table):
    order = table.primary_key.columns.values()[0]
    return [dict(row) for row in conn.execute(select(table).order_by(order)).mappings()]

def insert(conn, table, **data):
    conn.execute(table.insert().values(**data))
    return data

def update(conn, table, key, **data):
    pk = table.primary_key.columns.values()[0]
    conn.execute(table.update().where(pk == key).values(**data))
    return get(conn, table, key)
