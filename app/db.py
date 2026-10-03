import os, sqlite3, datetime
from flask import g, current_app

def now(): return datetime.datetime.now().isoformat(timespec="seconds")

def connect(path):
    c = sqlite3.connect(path, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); c.execute("PRAGMA journal_mode=WAL")
    return c

def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db

def close_db(e=None):
    d = g.pop("db", None)
    if d: d.close()

def init_db(path):
    c = connect(path)
    c.executescript(open(os.path.join(os.path.dirname(__file__), "schema.sql")).read())
    c.commit(); c.close()

def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows

def ex(sql, args=()):
    d = get_db(); cur = d.execute(sql, args); d.commit(); return cur.lastrowid

def audit(user_id, action, detail=""):
    ex("INSERT INTO audit_logs(at,user_id,action,detail) VALUES(?,?,?,?)", (now(), user_id, action, detail))
