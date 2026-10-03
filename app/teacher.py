import os, datetime, uuid, json
from flask import Blueprint, request, redirect, render_template, flash, session, jsonify, send_file, abort, current_app
from werkzeug.utils import secure_filename
from .auth import login_view, require, current_teacher
from .db import q, ex, audit, get_db, now
from . import pipeline, reports

bp = Blueprint("teacher", __name__)
T = require("teacher")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
EXT = {".jpg", ".jpeg", ".png", ".webp"}

@bp.route("/teacher/login", methods=["GET", "POST"])
def login(): return login_view("teacher")

def my_assignments(tid):
    return q("""SELECT a.id, a.subject_id, a.group_id, sub.name subject, sub.code, sem.number sem, g.label, g.name gname,
                (SELECT COUNT(*) FROM subject_group_students x WHERE x.group_id=g.id) n
                FROM teacher_assignments a JOIN subjects sub ON sub.id=a.subject_id JOIN subject_groups g ON g.id=a.group_id
                JOIN semesters sem ON sem.id=sub.semester_id WHERE a.teacher_id=? ORDER BY a.id""", (tid,))

def own_session(sid):
    t = current_teacher()
    s = q("""SELECT s.*, sub.name subject, sem.number sem, g.label glabel, g.name gname, u.full_name faculty
             FROM attendance_sessions s JOIN subjects sub ON sub.id=s.subject_id JOIN semesters sem ON sem.id=sub.semester_id
             JOIN subject_groups g ON g.id=s.group_id JOIN teachers te ON te.id=s.teacher_id JOIN users u ON u.id=te.user_id
             WHERE s.id=? AND s.teacher_id=?""", (sid, t["id"]), one=True)
    if not s: abort(404)
    return s

@bp.route("/teacher/dashboard")
@T
def dashboard():
    t = current_teacher(); wd = datetime.date.today().weekday()
    classes = q("""SELECT tt.id ttid, tt.hour_no, tt.start_time, tt.end_time, a.id aid, sub.name subject, sem.number sem, g.label, g.name gname
                   FROM timetable tt JOIN teacher_assignments a ON a.id=tt.assignment_id JOIN subjects sub ON sub.id=a.subject_id
                   JOIN semesters sem ON sem.id=sub.semester_id JOIN subject_groups g ON g.id=a.group_id
                   WHERE a.teacher_id=? AND tt.weekday=? ORDER BY tt.hour_no""", (t["id"], wd))
    sessions = q("""SELECT s.id, s.status, s.session_date, sub.name subject, g.label FROM attendance_sessions s JOIN subjects sub ON sub.id=s.subject_id
                    JOIN subject_groups g ON g.id=s.group_id WHERE s.teacher_id=? AND s.status!='finalized' ORDER BY s.id DESC""", (t["id"],))
    tot = q("""SELECT SUM(final_status='PRESENT') p, SUM(final_status='ABSENT') a, SUM(ai_result='REVIEW') r, SUM(ai_result='OTHER_CLASS') o
               FROM attendance_records r JOIN attendance_sessions s ON s.id=r.session_id WHERE s.teacher_id=? AND s.session_date=date('now','localtime')""",
            (t["id"],), one=True)
    return render_template("teacher/dashboard.html", classes=classes, sessions=sessions, tot=tot, today=datetime.date.today(), nav="dash")

@bp.route("/teacher/classes")
@T
def classes():
    t = current_teacher()
    asg = my_assignments(t["id"])
    tts = q("""SELECT tt.*, a.id aid FROM timetable tt JOIN teacher_assignments a ON a.id=tt.assignment_id WHERE a.teacher_id=? ORDER BY tt.weekday, tt.hour_no""", (t["id"],))
    return render_template("teacher/classes.html", asg=asg, tts=tts, days=DAYS, nav="classes")

@bp.route("/teacher/classes/start", methods=["POST"])
@T
def start():
    t = current_teacher()
    a = q("SELECT * FROM teacher_assignments WHERE id=? AND teacher_id=?", (request.form["assignment_id"], t["id"]), one=True)
    if not a: abort(403)
    tt = q("SELECT * FROM timetable WHERE id=?", (request.form.get("timetable_id") or 0,), one=True)
    if not tt:
        tt = q("SELECT * FROM timetable WHERE assignment_id=? ORDER BY (weekday=?) DESC, hour_no LIMIT 1", (a["id"], datetime.date.today().weekday()), one=True)
    sid = ex("""INSERT INTO attendance_sessions(assignment_id,teacher_id,subject_id,group_id,session_date,hour_no,start_time,end_time,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", (a["id"], t["id"], a["subject_id"], a["group_id"], datetime.date.today().isoformat(),
             tt["hour_no"] if tt else None, tt["start_time"] if tt else None, tt["end_time"] if tt else None, "open", now()))
    audit(session["uid"], "session_start", str(sid))
    return redirect("/teacher/attendance/%d" % sid)

@bp.route("/teacher/students")
@T
def students():
    t = current_teacher(); gid = request.args.get("group")
    asg = my_assignments(t["id"])
    if not gid and asg: gid = asg[0]["group_id"]
    rows = q("""SELECT st.usn, st.name, sec.name sec, (SELECT COUNT(*) FROM face_profiles fp WHERE fp.student_id=st.id) face
                FROM subject_group_students x JOIN students st ON st.id=x.student_id JOIN sections sec ON sec.id=st.section_id
                WHERE x.group_id=? AND x.group_id IN (SELECT group_id FROM teacher_assignments WHERE teacher_id=?) ORDER BY st.usn""", (gid, t["id"]))
    return render_template("teacher/students.html", rows=rows, asg=asg, gid=int(gid) if gid else None, nav="students")

@bp.route("/teacher/attendance/<int:sid>")
@T
def attendance(sid):
    s = own_session(sid)
    photos = q("SELECT * FROM attendance_photos WHERE session_id=? ORDER BY id", (sid,))
    roster = q("SELECT COUNT(*) FROM subject_group_students WHERE group_id=?", (s["group_id"],), one=True)[0]
    return render_template("teacher/attendance.html", s=s, photos=photos, roster=roster, stages=pipeline.STAGES, nav="classes")

@bp.route("/teacher/attendance/<int:sid>/upload", methods=["POST"])
@T
def upload(sid):
    s = own_session(sid)
    if s["status"] not in ("open", "failed"): flash("Photos are locked after processing."); return redirect("/teacher/attendance/%d" % sid)
    have = q("SELECT COUNT(*) FROM attendance_photos WHERE session_id=?", (sid,), one=True)[0]
    d = os.path.join(current_app.config["DATA_DIR"], "sessions", str(sid), "photos"); os.makedirs(d, exist_ok=True)
    added = 0
    for f in request.files.getlist("photos"):
        if not f or not f.filename: continue
        if have + added >= 4: flash("Maximum 4 photos per session."); break
        ext = os.path.splitext(f.filename)[1].lower() or ".jpg"
        if ext not in EXT: flash("Skipped %s (not an image)." % f.filename); continue
        name = secure_filename(f.filename) or "photo%d%s" % (have + added + 1, ext)
        path = os.path.join(d, "%s_%s" % (uuid.uuid4().hex[:6], name)); f.save(path)
        ex("INSERT INTO attendance_photos(session_id,filename,path) VALUES(?,?,?)", (sid, name, path)); added += 1
    flash("%d photo(s) added." % added)
    total = q("SELECT COUNT(*) FROM attendance_photos WHERE session_id=?", (sid,), one=True)[0]
    if request.form.get("run") == "1" and 3 <= total <= 4:      # one-tap demo flow: upload -> AI processing starts automatically
        return redirect("/teacher/attendance/%d?autorun=1" % sid)
    return redirect("/teacher/attendance/%d" % sid)

@bp.route("/teacher/attendance/<int:sid>/photo/<int:pid>/delete", methods=["POST"])
@T
def photo_delete(sid, pid):
    s = own_session(sid)
    if s["status"] in ("open", "failed"): ex("DELETE FROM attendance_photos WHERE id=? AND session_id=?", (pid, sid))
    return redirect("/teacher/attendance/%d" % sid)

@bp.route("/teacher/attendance/<int:sid>/process", methods=["POST"])
@T
def process(sid):
    s = own_session(sid)
    n = q("SELECT COUNT(*) FROM attendance_photos WHERE session_id=?", (sid,), one=True)[0]
    if n < 3 or n > 4:
        return jsonify(error="Upload 3 to 4 classroom photos first (you have %d)." % n), 400
    if s["status"] == "processing": return jsonify(ok=True)
    if s["status"] not in ("open", "failed"):      # review / finalized sessions are never re-processed (would erase decisions / final attendance)
        return jsonify(error="This session is already %s and cannot be re-processed." % s["status"]), 409
    ex("UPDATE attendance_sessions SET status='processing', stage=1, stage_msg='Uploading photos', error=NULL WHERE id=?", (sid,))
    pipeline.start_async(current_app._get_current_object(), sid)
    audit(session["uid"], "process_start", str(sid))
    return jsonify(ok=True)

@bp.route("/teacher/attendance/<int:sid>/status")
@T
def status(sid):
    s = own_session(sid)
    return jsonify(status=s["status"], stage=s["stage"], msg=s["stage_msg"], error=s["error"])

def review_rows(sid, s):
    det = q("""SELECT r.*, st.usn, st.name, sec.name sec FROM attendance_records r LEFT JOIN students st ON st.id=r.student_id
               LEFT JOIN sections sec ON sec.id=st.section_id WHERE r.session_id=? AND r.ai_result!='NOT_DETECTED'
               ORDER BY CASE r.ai_result WHEN 'REVIEW' THEN 0 WHEN 'UNKNOWN' THEN 1 WHEN 'OTHER_CLASS' THEN 2 ELSE 3 END, st.usn""", (sid,))
    seen = {r["student_id"] for r in q("SELECT student_id FROM attendance_records WHERE session_id=? AND student_id IS NOT NULL", (sid,))}
    roster = q("""SELECT st.id, st.usn, st.name, sec.name sec FROM subject_group_students x JOIN students st ON st.id=x.student_id
                  JOIN sections sec ON sec.id=st.section_id WHERE x.group_id=? ORDER BY st.usn""", (s["group_id"],))
    manual = {r["student_id"] for r in q("SELECT student_id FROM attendance_records WHERE session_id=? AND ai_result='NOT_DETECTED' AND teacher_decision='PRESENT'", (sid,))}
    notdet = [r for r in roster if r["id"] not in seen or r["id"] in manual]
    return det, notdet, manual

@bp.route("/teacher/attendance/<int:sid>/review")
@T
def review(sid):
    s = own_session(sid)
    if s["status"] not in ("review", "finalized"): return redirect("/teacher/attendance/%d" % sid)
    det, notdet, manual = review_rows(sid, s)
    counts = {k: sum(1 for r in det if r["ai_result"] == k) for k in ("PRESENT", "REVIEW", "OTHER_CLASS", "UNKNOWN")}
    photos = q("SELECT * FROM attendance_photos WHERE session_id=? ORDER BY id", (sid,))
    return render_template("teacher/review.html", s=s, det=det, notdet=notdet, manual=manual, counts=counts, photos=photos,
                           roster=q("""SELECT st.id, st.usn, st.name FROM subject_group_students x JOIN students st ON st.id=x.student_id WHERE x.group_id=? ORDER BY st.usn""", (s["group_id"],)),
                           pipeline_msg=s["stage_msg"], locked=s["status"] == "finalized", nav="classes")

@bp.route("/teacher/attendance/<int:sid>/review/save", methods=["POST"])
@T
def review_save(sid):
    s = own_session(sid)
    if s["status"] != "review": abort(400)
    db = get_db(); f = request.form
    for r in db.execute("SELECT id, ai_result FROM attendance_records WHERE session_id=? AND ai_result IN ('PRESENT','REVIEW')", (sid,)).fetchall():
        v = f.get("dec_%d" % r["id"])
        if v in ("PRESENT", "ABSENT"): db.execute("UPDATE attendance_records SET teacher_decision=? WHERE id=?", (v, r["id"]))
    for r in db.execute("SELECT id FROM attendance_records WHERE session_id=? AND ai_result='UNKNOWN'", (sid,)).fetchall():
        v = f.get("unk_%d" % r["id"])
        if v and v.isdigit():
            clash = db.execute("SELECT 1 FROM attendance_records WHERE session_id=? AND student_id=? AND id!=?", (sid, int(v), r["id"])).fetchone()
            if not clash:
                db.execute("UPDATE attendance_records SET student_id=?, teacher_decision='PRESENT', note='identified by teacher' WHERE id=?", (int(v), r["id"]))
    db.commit()
    for k in f:   # manual present for roster students the AI did not see
        if k.startswith("man_"):
            stid = int(k[4:]); present = f[k] == "PRESENT"
            row = db.execute("SELECT id FROM attendance_records WHERE session_id=? AND student_id=? AND ai_result='NOT_DETECTED'", (sid, stid)).fetchone()
            if present and not row:
                db.execute("INSERT INTO attendance_records(session_id,student_id,ai_result,teacher_decision,note) VALUES(?,?,?,?,?)", (sid, stid, "NOT_DETECTED", "PRESENT", "marked present by teacher"))
            elif row: db.execute("UPDATE attendance_records SET teacher_decision=? WHERE id=?", ("PRESENT" if present else "ABSENT", row["id"]))
    db.commit()
    if request.form.get("finalize") == "1": return finalize(sid)
    flash("Decisions saved."); return redirect("/teacher/attendance/%d/review" % sid)

def finalize(sid):
    s = own_session(sid); db = get_db()
    pending = db.execute("SELECT COUNT(*) FROM attendance_records WHERE session_id=? AND ai_result='REVIEW' AND teacher_decision IS NULL", (sid,)).fetchone()[0]
    if pending:
        flash("Decide the %d REVIEW student(s) first (Present or Absent)." % pending); return redirect("/teacher/attendance/%d/review" % sid)
    roster = [r["student_id"] for r in db.execute("SELECT student_id FROM subject_group_students WHERE group_id=?", (s["group_id"],))]
    for r in db.execute("SELECT * FROM attendance_records WHERE session_id=?", (sid,)).fetchall():
        if r["ai_result"] == "OTHER_CLASS": fs = "OTHER_CLASS"
        elif r["student_id"] is None: fs = "UNKNOWN"
        else: fs = "PRESENT" if r["teacher_decision"] == "PRESENT" else "ABSENT"
        db.execute("UPDATE attendance_records SET final_status=? WHERE id=?", (fs, r["id"]))
    present = {r["student_id"] for r in db.execute("SELECT student_id FROM attendance_records WHERE session_id=? AND final_status='PRESENT'", (sid,))}
    have = {r["student_id"] for r in db.execute("SELECT student_id FROM attendance_records WHERE session_id=? AND student_id IS NOT NULL", (sid,))}
    for st in roster:   # ABSENT = eligible roster - teacher-confirmed present
        if st not in present and st not in have:
            db.execute("INSERT INTO attendance_records(session_id,student_id,ai_result,final_status,teacher_decision) VALUES(?,?,?,?,?)", (sid, st, "NOT_DETECTED", "ABSENT", "ABSENT"))
    db.execute("UPDATE attendance_sessions SET status='finalized', finalized_at=? WHERE id=?", (now(), sid)); db.commit()
    dd = current_app.config["DATA_DIR"]
    reports.attendance_pdf(db, dd, sid); reports.other_class_pdf(db, dd, sid)
    audit(session["uid"], "finalize", str(sid))
    flash("Attendance finalized. Reports generated.")
    return redirect("/teacher/reports?highlight=%d" % sid)

@bp.route("/teacher/attendance/<int:sid>/other-class")
@T
def other_class(sid):
    s = own_session(sid)
    rows = q("""SELECT o.*, st.usn, st.name, sec.name sec, sem.number sem, r.crop_path FROM other_class_detections o JOIN students st ON st.id=o.student_id
                JOIN sections sec ON sec.id=st.section_id JOIN semesters sem ON sem.id=st.semester_id LEFT JOIN attendance_records r ON r.id=o.record_id
                WHERE o.session_id=? ORDER BY st.usn""", (sid,))
    rep = q("SELECT * FROM attendance_reports WHERE session_id=? AND kind='other_class'", (sid,), one=True)
    return render_template("teacher/other_class.html", s=s, rows=rows, rep=rep, nav="classes")

@bp.route("/teacher/reports")
@T
def reports_page():
    t = current_teacher()
    rows = q("""SELECT s.id, s.session_date, s.hour_no, sub.name subject, g.label,
                (SELECT COUNT(*) FROM attendance_records r WHERE r.session_id=s.id AND r.final_status='PRESENT') p,
                (SELECT COUNT(*) FROM attendance_records r WHERE r.session_id=s.id AND r.final_status='ABSENT') a,
                (SELECT COUNT(*) FROM attendance_records r WHERE r.session_id=s.id AND r.ai_result='OTHER_CLASS') o
                FROM attendance_sessions s JOIN subjects sub ON sub.id=s.subject_id JOIN subject_groups g ON g.id=s.group_id
                WHERE s.teacher_id=? AND s.status='finalized' ORDER BY s.id DESC""", (t["id"],))
    return render_template("teacher/reports.html", rows=rows, hl=request.args.get("highlight"), nav="reports")

@bp.route("/teacher/profile")
@T
def profile():
    t = current_teacher()
    return render_template("teacher/profile.html", t=t, asg=my_assignments(t["id"]), nav="profile")

# ---------- protected files ----------
@bp.route("/teacher/files/crop/<int:rid>")
@T
def f_crop(rid):
    r = q("""SELECT r.crop_path FROM attendance_records r JOIN attendance_sessions s ON s.id=r.session_id WHERE r.id=? AND s.teacher_id=?""", (rid, current_teacher()["id"]), one=True)
    if not r or not r["crop_path"]: abort(404)
    return send_file(r["crop_path"])

@bp.route("/teacher/files/photo/<int:pid>")
@T
def f_photo(pid):
    p = q("""SELECT p.* FROM attendance_photos p JOIN attendance_sessions s ON s.id=p.session_id WHERE p.id=? AND s.teacher_id=?""", (pid, current_teacher()["id"]), one=True)
    if not p: abort(404)
    path = p["annotated_path"] if request.args.get("a") and p["annotated_path"] else p["path"]
    return send_file(path)

@bp.route("/teacher/files/report/<int:sid>/<kind>.pdf")
@T
def f_report(sid, kind):
    own_session(sid)
    if kind not in ("attendance", "other_class"): abort(404)
    r = q("SELECT path FROM attendance_reports WHERE session_id=? AND kind=?", (sid, kind), one=True)
    if not r: abort(404)
    return send_file(r["path"], mimetype="application/pdf", download_name="%s_session_%d.pdf" % (kind, sid), as_attachment=request.args.get("dl") == "1")
