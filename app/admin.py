import cv2, numpy as np
from flask import Blueprint, request, redirect, render_template, flash, session
from werkzeug.security import generate_password_hash
from .auth import login_view, require
from .db import q, ex, audit, get_db
from . import ai, enroll

bp = Blueprint("admin", __name__, url_prefix="/admin")
A = require("admin")
PER = 40

@bp.route("/login", methods=["GET", "POST"])
def login(): return login_view("admin")

@bp.route("/dashboard")
@A
def dashboard():
    one = lambda s: q(s, one=True)[0]
    stats = {"Total Students": one("SELECT COUNT(*) FROM students"), "Teachers": one("SELECT COUNT(*) FROM teachers"),
             "Subjects": one("SELECT COUNT(*) FROM subjects"), "Attendance Sessions": one("SELECT COUNT(*) FROM attendance_sessions"),
             "Today's Attendance": one("SELECT COUNT(*) FROM attendance_sessions WHERE session_date=date('now','localtime')"),
             "Face profiles": one("SELECT COUNT(*) FROM face_profiles")}
    recent = q("""SELECT s.id, s.session_date, s.status, sub.name subject, u.full_name faculty FROM attendance_sessions s
                  JOIN subjects sub ON sub.id=s.subject_id JOIN teachers t ON t.id=s.teacher_id JOIN users u ON u.id=t.user_id
                  ORDER BY s.id DESC LIMIT 6""")
    return render_template("admin/dashboard.html", stats=stats, recent=recent, nav="dashboard")

# ---------- students ----------
@bp.route("/students")
@A
def students():
    sec, s, page = request.args.get("section", ""), request.args.get("q", "").strip(), int(request.args.get("page", 1))
    where, args = "WHERE 1=1", []
    if sec: where += " AND sec.name=?"; args.append(sec)
    if s: where += " AND (st.usn LIKE ? OR st.name LIKE ?)"; args += ["%" + s + "%"] * 2
    total = q("SELECT COUNT(*) FROM students st JOIN sections sec ON sec.id=st.section_id " + where, args, one=True)[0]
    rows = q("""SELECT st.*, sec.name sec, (SELECT COUNT(*) FROM face_profiles fp WHERE fp.student_id=st.id) face
                FROM students st JOIN sections sec ON sec.id=st.section_id """ + where + " ORDER BY st.usn LIMIT ? OFFSET ?",
             args + [PER, (page - 1) * PER])
    edit = q("SELECT * FROM students WHERE id=?", (request.args.get("edit"),), one=True) if request.args.get("edit") else None
    return render_template("admin/students.html", rows=rows, total=total, page=page, per=PER, sec=sec, s=s, edit=edit,
                           sections=q("SELECT * FROM sections ORDER BY name"), nav="students")

@bp.route("/students/save", methods=["POST"])
@A
def student_save():
    f = request.form; sid = f.get("id")
    sec = q("SELECT * FROM sections WHERE id=?", (f["section_id"],), one=True)
    try:
        if sid:
            ex("UPDATE students SET usn=?,name=?,section_id=? WHERE id=?", (f["usn"].strip(), f["name"].strip(), sec["id"], sid))
        else:
            ex("INSERT INTO students(usn,name,department_id,semester_id,section_id) VALUES(?,?,?,?,?)",
               (f["usn"].strip(), f["name"].strip(), sec["department_id"], sec["semester_id"], sec["id"]))
        audit(session["uid"], "student_save", f["usn"]); flash("Student saved.")
    except Exception as e:
        flash("Could not save: %s" % e)
    return redirect("/admin/students")

# ---------- subject enrollment ----------
@bp.route("/students/enrollment")
@A
def enrollment():
    gid = request.args.get("group") or (q("SELECT id FROM subject_groups ORDER BY id LIMIT 1", one=True) or {"id": None})["id"]
    groups = q("""SELECT g.*, sub.name subject, (SELECT COUNT(*) FROM subject_group_students x WHERE x.group_id=g.id) n
                  FROM subject_groups g JOIN subjects sub ON sub.id=g.subject_id ORDER BY g.id""")
    members = q("""SELECT st.id, st.usn, st.name, sec.name sec FROM subject_group_students x JOIN students st ON st.id=x.student_id
                   JOIN sections sec ON sec.id=st.section_id WHERE x.group_id=? ORDER BY st.usn""", (gid,)) if gid else []
    return render_template("admin/enrollment.html", groups=groups, gid=int(gid) if gid else None, members=members,
                           sections=q("SELECT * FROM sections ORDER BY name"), nav="enroll")

@bp.route("/students/enrollment/update", methods=["POST"])
@A
def enrollment_update():
    f = request.form; gid = f["group_id"]; act = f["action"]
    if act == "add_section":
        ex("INSERT OR IGNORE INTO subject_group_students SELECT ?, id FROM students WHERE section_id=?", (gid, f["section_id"]))
    elif act == "add_range":
        ex("INSERT OR IGNORE INTO subject_group_students SELECT ?, id FROM students WHERE usn BETWEEN ? AND ?",
           (gid, f["from_usn"].strip(), f["to_usn"].strip()))
    elif act == "remove":
        ex("DELETE FROM subject_group_students WHERE group_id=? AND student_id=?", (gid, f["student_id"]))
    elif act == "clear_section":
        ex("DELETE FROM subject_group_students WHERE group_id=? AND student_id IN (SELECT id FROM students WHERE section_id=?)", (gid, f["section_id"]))
    audit(session["uid"], "enrollment_" + act, "group %s" % gid)
    return redirect("/admin/students/enrollment?group=%s" % gid)

# ---------- face enrolment ----------
@bp.route("/face-enrollment")
@A
def face_enrollment():
    s, only = request.args.get("q", "").strip(), request.args.get("only", "")
    where, args = "WHERE 1=1", []
    if s: where += " AND (st.usn LIKE ? OR st.name LIKE ?)"; args += ["%" + s + "%"] * 2
    if only == "enrolled": where += " AND EXISTS(SELECT 1 FROM face_profiles fp WHERE fp.student_id=st.id)"
    rows = q("""SELECT st.id, st.usn, st.name, sec.name sec,
                (SELECT COUNT(*) FROM face_embeddings fe JOIN face_profiles fp ON fp.id=fe.profile_id WHERE fp.student_id=st.id) n
                FROM students st JOIN sections sec ON sec.id=st.section_id """ + where + " ORDER BY st.usn LIMIT 60", args)
    tot = q("SELECT COUNT(*) FROM face_profiles", one=True)[0]
    return render_template("admin/face_enrollment.html", rows=rows, s=s, only=only, tot=tot, nav="face")

@bp.route("/face-enrollment/<int:sid>", methods=["POST"])
@A
def face_upload(sid):
    imgs = []
    for f in request.files.getlist("photos"):
        if f and f.filename:
            try: imgs.append(ai.read_image(f.read()))
            except ValueError: pass
    ok, errs = enroll.enroll_images(get_db(), sid, imgs)
    flash("Enrolled %d photo(s)." % ok + ((" Skipped: " + "; ".join(errs)) if errs else ""))
    audit(session["uid"], "face_enroll", "student %s ok=%d" % (sid, ok))
    return redirect("/admin/face-enrollment")

@bp.route("/face-enrollment/<int:sid>/delete", methods=["POST"])
@A
def face_delete(sid):
    ex("DELETE FROM face_profiles WHERE student_id=?", (sid,)); flash("Face profile removed."); return redirect("/admin/face-enrollment")

@bp.route("/face-enrollment/demo-gallery", methods=["POST"])
@A
def face_demo_gallery():
    from flask import current_app
    n = enroll.enroll_demo_gallery(get_db(), current_app.config["ASSET_DIR"])
    flash("Enrolled demo gallery for %d student(s)." % n); return redirect("/admin/face-enrollment")

# ---------- subjects / groups ----------
@bp.route("/subjects", methods=["GET", "POST"])
@A
def subjects():
    if request.method == "POST":
        f = request.form
        try:
            ex("INSERT INTO subjects(code,name,department_id,semester_id,kind) VALUES(?,?,?,?,?)",
               (f["code"].strip(), f["name"].strip(), 1, q("SELECT id FROM semesters WHERE number=?", (f["semester"],), one=True)["id"], f["kind"]))
            flash("Subject added.")
        except Exception as e: flash("Could not add: %s" % e)
        return redirect("/admin/subjects")
    rows = q("SELECT s.*, sem.number sem, (SELECT COUNT(*) FROM subject_groups g WHERE g.subject_id=s.id) ng FROM subjects s JOIN semesters sem ON sem.id=s.semester_id ORDER BY s.id")
    return render_template("admin/subjects.html", rows=rows, nav="subjects")

@bp.route("/subject-groups", methods=["GET", "POST"])
@A
def subject_groups():
    if request.method == "POST":
        f = request.form
        if f.get("delete"):
            ex("DELETE FROM subject_group_students WHERE group_id=?", (f["delete"],)); ex("DELETE FROM subject_groups WHERE id=?", (f["delete"],))
        else:
            ex("INSERT INTO subject_groups(subject_id,name,label) VALUES(?,?,?)", (f["subject_id"], f["name"].strip(), f["label"].strip()))
        return redirect("/admin/subject-groups")
    rows = q("""SELECT g.*, sub.name subject, (SELECT COUNT(*) FROM subject_group_students x WHERE x.group_id=g.id) n
                FROM subject_groups g JOIN subjects sub ON sub.id=g.subject_id ORDER BY g.id""")
    return render_template("admin/subject_groups.html", rows=rows, subjects=q("SELECT * FROM subjects"), nav="groups")

# ---------- teachers / assignments / timetable ----------
@bp.route("/teachers", methods=["GET", "POST"])
@A
def teachers():
    if request.method == "POST":
        f = request.form
        try:
            uid = ex("INSERT INTO users(email,password_hash,role,full_name) VALUES(?,?,?,?)",
                     (f["email"].strip(), generate_password_hash(f["password"]), "teacher", f["name"].strip()))
            ex("INSERT INTO teachers(user_id,department_id,designation) VALUES(?,?,?)", (uid, 1, f.get("designation", "Assistant Professor")))
            flash("Teacher added.")
        except Exception as e: flash("Could not add: %s" % e)
        return redirect("/admin/teachers")
    rows = q("""SELECT t.id, u.full_name, u.email, t.designation, (SELECT COUNT(*) FROM teacher_assignments a WHERE a.teacher_id=t.id) n
                FROM teachers t JOIN users u ON u.id=t.user_id""")
    return render_template("admin/teachers.html", rows=rows, nav="teachers")

@bp.route("/teacher-assignments", methods=["GET", "POST"])
@A
def assignments():
    if request.method == "POST":
        f = request.form
        if f.get("delete"):
            ex("DELETE FROM timetable WHERE assignment_id=?", (f["delete"],)); ex("DELETE FROM teacher_assignments WHERE id=?", (f["delete"],))
        else:
            g = q("SELECT * FROM subject_groups WHERE id=?", (f["group_id"],), one=True)
            ex("INSERT OR IGNORE INTO teacher_assignments(teacher_id,subject_id,group_id) VALUES(?,?,?)", (f["teacher_id"], g["subject_id"], g["id"]))
        return redirect("/admin/teacher-assignments")
    rows = q("""SELECT a.id, u.full_name teacher, sub.name subject, g.label, g.name gname FROM teacher_assignments a JOIN teachers t ON t.id=a.teacher_id
                JOIN users u ON u.id=t.user_id JOIN subjects sub ON sub.id=a.subject_id JOIN subject_groups g ON g.id=a.group_id ORDER BY a.id""")
    return render_template("admin/assignments.html", rows=rows, nav="assign",
                           teachers=q("SELECT t.id, u.full_name FROM teachers t JOIN users u ON u.id=t.user_id"),
                           groups=q("SELECT g.id, sub.name||' — '||g.name n FROM subject_groups g JOIN subjects sub ON sub.id=g.subject_id"))

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
@bp.route("/timetable", methods=["GET", "POST"])
@A
def timetable():
    if request.method == "POST":
        f = request.form
        if f.get("delete"): ex("DELETE FROM timetable WHERE id=?", (f["delete"],))
        else:
            for d in f.getlist("weekday"):
                ex("INSERT INTO timetable(assignment_id,weekday,hour_no,start_time,end_time) VALUES(?,?,?,?,?)",
                   (f["assignment_id"], d, f["hour_no"], f["start_time"], f["end_time"]))
        return redirect("/admin/timetable")
    rows = q("""SELECT tt.*, sub.name subject, g.label, u.full_name teacher FROM timetable tt JOIN teacher_assignments a ON a.id=tt.assignment_id
                JOIN subjects sub ON sub.id=a.subject_id JOIN subject_groups g ON g.id=a.group_id JOIN teachers t ON t.id=a.teacher_id
                JOIN users u ON u.id=t.user_id ORDER BY tt.weekday, tt.hour_no""")
    asg = q("""SELECT a.id, sub.name||' — '||g.label||' ('||u.full_name||')' n FROM teacher_assignments a JOIN subjects sub ON sub.id=a.subject_id
               JOIN subject_groups g ON g.id=a.group_id JOIN teachers t ON t.id=a.teacher_id JOIN users u ON u.id=t.user_id""")
    return render_template("admin/timetable.html", rows=rows, asg=asg, days=DAYS, nav="tt")
