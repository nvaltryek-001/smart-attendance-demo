import os
from flask import Flask, session, redirect, render_template, send_from_directory, abort, request
from . import db as dbm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLLEGE = "Sai Vidya Institute of Technology"

def create_app(cfg=None):
    app = Flask(__name__)
    data = os.environ.get("DATA_DIR", os.path.join(ROOT, "data"))
    app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "demo-only-not-secret"), DATA_DIR=data,
                      DB_PATH=os.path.join(data, "demo.sqlite3"),
                      ASSET_DIR=os.environ.get("ASSET_DIR", os.path.join(ROOT, "demo_assets")),
                      MAX_CONTENT_LENGTH=60 * 1024 * 1024, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True,
                      PERMANENT_SESSION_LIFETIME=60 * 60 * 12)
    if cfg: app.config.update(cfg)
    os.makedirs(os.path.join(app.config["DATA_DIR"], "sessions"), exist_ok=True)
    dbm.init_db(app.config["DB_PATH"])
    app.teardown_appcontext(dbm.close_db)
    if os.environ.get("AUTO_SEED", "1") == "1" and not app.config.get("NO_SEED"):
        from .seed import seed
        seed(app)

    from .admin import bp as admin_bp
    from .teacher import bp as teacher_bp
    app.register_blueprint(admin_bp); app.register_blueprint(teacher_bp)

    @app.context_processor
    def inject():
        u = dbm.q("SELECT id,email,role,full_name FROM users WHERE id=?", (session["uid"],), one=True) if session.get("uid") else None
        return {"me": u, "demo": True, "college": COLLEGE}

    @app.route("/")
    def home():
        d = os.path.join(app.config["ASSET_DIR"], "classroom")
        files = sorted(f for f in os.listdir(d) if f.endswith(".jpg")) if os.path.isdir(d) else []
        return render_template("home.html", files=files)

    @app.route("/demo/classroom/<name>")
    def demo_classroom(name):
        d = os.path.join(app.config["ASSET_DIR"], "classroom")
        if not name.startswith("classroom_") or not name.endswith(".jpg"): abort(404)
        return send_from_directory(d, name, as_attachment=bool(request.args.get("dl")))

    @app.route("/logout")
    def logout():
        session.clear(); return redirect("/")

    @app.route("/health")
    def health(): return {"ok": True}

    @app.errorhandler(404)
    def nf(e): return "Not found", 404
    return app
