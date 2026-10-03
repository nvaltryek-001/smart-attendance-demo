from functools import wraps
from flask import render_template, request, redirect, session, flash
from werkzeug.security import check_password_hash
from .db import q, audit

def require(role):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if session.get("role") != role or not session.get("uid"):
                return redirect("/%s/login" % role)
            return f(*a, **k)
        return w
    return deco

def current_teacher():
    return q("SELECT t.*, u.full_name, u.email FROM teachers t JOIN users u ON u.id=t.user_id WHERE t.user_id=?",
             (session.get("uid"),), one=True)

def login_view(role):
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE email=? AND role=?", (request.form.get("email", "").strip().lower(), role), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear(); session.permanent = True
            session["uid"], session["role"] = u["id"], role
            audit(u["id"], "login", role)
            return redirect("/%s/dashboard" % role)
        flash("Wrong email or password.")
    return render_template("login.html", role=role)
