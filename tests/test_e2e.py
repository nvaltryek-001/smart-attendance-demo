"""Local end-to-end acceptance test (mirrors the 25-step demo checklist).

Everything runs through the real Flask routes, the real InsightFace pipeline and the real PDF generator.
demo_assets/manifest.json is used ONLY at the end to VALIDATE results; the application never reads it.
Run:  pytest -s tests/test_e2e.py
"""
import os, io, json, time, sqlite3, shutil, subprocess, tempfile
import pytest
from app import create_app

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "demo_assets")
STEP = [0]
def step(msg): STEP[0] += 1; print("  [step %02d] %s" % (STEP[0], msg), flush=True)

pytestmark = pytest.mark.skipif(not os.path.isdir(os.path.join(ASSETS, "classroom")),
                                reason="demo_assets not built (python scripts/build_demo_assets.py)")

def login(c, role, email, pw):
    return c.post("/%s/login" % role, data={"email": email, "password": pw})

def usn(n): return "01DEMO23DS%03d" % n

def upload_and_process(c, sid, files=None):
    files = files or ["classroom_0%d.jpg" % i for i in range(1, 5)]
    data = {"photos": [(open(os.path.join(ASSETS, "classroom", f), "rb"), f) for f in files]}
    r = c.post("/teacher/attendance/%d/upload" % sid, data=data, content_type="multipart/form-data")
    assert r.status_code == 302
    r = c.post("/teacher/attendance/%d/process" % sid); assert r.status_code == 200, r.get_json()
    t0, seen = time.time(), []
    while time.time() - t0 < 300:
        s = c.get("/teacher/attendance/%d/status" % sid).get_json()
        if s["stage"] not in seen: seen.append(s["stage"])
        if s["status"] in ("review", "failed"): break
        time.sleep(0.3)
    assert s["status"] == "review", s
    return seen, s

def records(db_path, sid):
    db = sqlite3.connect(db_path); db.row_factory = sqlite3.Row
    rows = db.execute("""SELECT r.*, st.usn FROM attendance_records r LEFT JOIN students st ON st.id=r.student_id WHERE r.session_id=?""", (sid,)).fetchall()
    db.close(); return rows

def pdf_text(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout

@pytest.fixture(scope="module")
def env():
    d = tempfile.mkdtemp(prefix="smartatt_")
    cfg = {"DATA_DIR": d, "DB_PATH": os.path.join(d, "demo.sqlite3"), "TESTING": True}
    yield d, cfg
    shutil.rmtree(d, ignore_errors=True)

def test_full_demo_flow(env):
    d, cfg = env
    app = create_app(cfg); db_path = cfg["DB_PATH"]
    admin, t1, t2, anon = app.test_client(), app.test_client(), app.test_client(), app.test_client()

    # ---- access control before login
    for u in ("/admin/dashboard", "/teacher/dashboard", "/teacher/attendance/1", "/teacher/files/report/1/attendance.pdf"):
        assert anon.get(u).status_code == 302, u
    assert login(anon, "admin", "admin.demo@college.edu", "wrong").status_code == 200   # stays on login page

    # ---- ADMIN
    step("Admin login")
    r = login(admin, "admin", "admin.demo@college.edu", "Admin@12345"); assert r.status_code == 302
    html = admin.get("/admin/dashboard").get_data(as_text=True)
    assert "DEMO MODE" in html and "Total Students" in html and ">128<" in html.replace(" ", "")
    step("128 demo students visible (Section A 001-064, Section B 065-128)")
    html = admin.get("/admin/students").get_data(as_text=True)
    assert "128" in html and usn(1) in html and "Student 001" in html
    assert usn(65) in admin.get("/admin/students?section=B").get_data(as_text=True)
    assert usn(1) not in admin.get("/admin/students?section=B").get_data(as_text=True)
    step("Add + edit a demo student")
    admin.post("/admin/students/save", data={"usn": "01DEMO23DS999", "name": "Student 999", "section_id": 1})
    assert "01DEMO23DS999" in admin.get("/admin/students?q=999").get_data(as_text=True)
    step("Subjects, subject groups, enrollment, teachers, assignments, timetable pages")
    assert "Data Science" in admin.get("/admin/subjects").get_data(as_text=True)
    h = admin.get("/admin/subject-groups").get_data(as_text=True); assert "Cloud Computing" in h and "A+B" in h
    h = admin.get("/admin/students/enrollment?group=2").get_data(as_text=True); assert usn(65) in h and usn(1) in h
    assert "Demo Teacher" in admin.get("/admin/teachers").get_data(as_text=True)
    assert "Data Science" in admin.get("/admin/teacher-assignments").get_data(as_text=True)
    assert "09:00" in admin.get("/admin/timetable").get_data(as_text=True)
    step("Face enrollment page: 18 face profiles built from gallery images by InsightFace")
    h = admin.get("/admin/face-enrollment").get_data(as_text=True); assert "18" in h
    # distractors: an unassigned subject, and a 2nd teacher with her own class
    admin.post("/admin/subjects", data={"code": "DEMO-ML703", "name": "Machine Learning", "semester": 7, "kind": "core"})
    admin.post("/admin/teachers", data={"name": "Prof. Other", "email": "other.demo@college.edu", "password": "Demo@12345"})
    admin.post("/admin/subject-groups", data={"subject_id": 3, "name": "Machine Learning – B", "label": "Section B"})
    admin.post("/admin/students/enrollment/update", data={"group_id": 3, "action": "add_section", "section_id": 2})
    admin.post("/admin/teacher-assignments", data={"teacher_id": 2, "group_id": 3})
    step("Admin logout"); assert admin.get("/logout").status_code == 302
    assert admin.get("/admin/dashboard").status_code == 302

    # ---- TEACHER
    step("Teacher login")
    assert login(anon, "teacher", "teacher.demo@college.edu", "Admin@12345").status_code == 200    # admin pw must fail
    assert login(t1, "teacher", "teacher.demo@college.edu", "Demo@12345").status_code == 302
    assert t1.get("/admin/dashboard").status_code == 302          # teacher cannot open admin
    step("Teacher sees ONLY assigned classes (Data Science + Cloud Computing, not Machine Learning)")
    h = t1.get("/teacher/dashboard").get_data(as_text=True)
    assert "Data Science" in h and "Cloud Computing" in h and "Machine Learning" not in h and "DEMO MODE" in h
    assert "09:00" in h and "START ATTENDANCE" in h.upper()
    assert "Machine Learning" not in t1.get("/teacher/classes").get_data(as_text=True)
    ts = t1.get("/teacher/students").get_data(as_text=True); assert usn(1) in ts and usn(65) not in ts   # only own roster

    step("Start Data Science attendance")
    r = t1.post("/teacher/classes/start", data={"assignment_id": 1}); sid = int(r.headers["Location"].rsplit("/", 1)[1])
    h = t1.get("/teacher/attendance/%d" % sid).get_data(as_text=True)
    assert "Data Science" in h and "Section A" in h
    assert login(t2, "teacher", "other.demo@college.edu", "Demo@12345").status_code == 302
    assert t2.get("/teacher/attendance/%d" % sid).status_code == 404       # other teacher cannot open it
    assert t2.post("/teacher/classes/start", data={"assignment_id": 1}).status_code == 403
    r = t1.post("/teacher/attendance/%d/process" % sid); assert r.status_code == 400    # needs 3-4 photos

    step("Upload classroom_01..04.jpg and run ACTUAL AI processing")
    seen_stages, s = upload_and_process(t1, sid)
    print("      stages observed:", seen_stages, "|", s["msg"])
    assert {3, 4, 9} <= set(seen_stages) and max(seen_stages) == 9      # fast stages (quality check) can finish between polls
    t1.post("/teacher/attendance/%d/upload" % sid, data={"photos": [(io.BytesIO(b"x"), "extra.jpg")]}, content_type="multipart/form-data")
    assert sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM attendance_photos WHERE session_id=?", (sid,)).fetchone()[0] == 4   # 5th photo refused

    recs = records(db_path, sid)
    by = {k: sorted(r["usn"] for r in recs if r["ai_result"] == k and r["usn"]) for k in ("PRESENT", "REVIEW", "OTHER_CLASS")}
    unknown = [r for r in recs if r["ai_result"] == "UNKNOWN"]
    photos = sqlite3.connect(db_path).execute("SELECT filename,faces_detected FROM attendance_photos WHERE session_id=?", (sid,)).fetchall()
    print("      PRESENT", len(by["PRESENT"]), "REVIEW", by["REVIEW"], "OTHER_CLASS", by["OTHER_CLASS"], "UNKNOWN", len(unknown), "| faces/photo", photos)

    step("Validate recognition against the manifest (validation only, written independently of the app)")
    man = json.load(open(os.path.join(ASSETS, "manifest.json")))
    all_ids = {u for lst in man["photos"].values() for u in lst}
    enrolled_A = sorted(u for u in all_ids if u.startswith("01DEMO") and int(u[-3:]) <= 64)
    enrolled_B = sorted(u for u in all_ids if u.startswith("01DEMO") and int(u[-3:]) >= 65)
    strangers = sorted(u for u in all_ids if not u.startswith("01DEMO"))
    assert sorted(by["PRESENT"] + by["REVIEW"]) == enrolled_A
    assert by["REVIEW"] == [man["review_student"]]
    assert by["OTHER_CLASS"] == enrolled_B and len(enrolled_B) >= 2
    assert len(unknown) == len(strangers) == 2 and all(r["student_id"] is None for r in unknown)
    assert sum(f for _, f in photos) == sum(len(v) for v in man["photos"].values())      # every placed face detected
    step("Deduplication: students seen in several photos are one row each")
    multi = [r for r in recs if (r["seen_in_photos"] or 1) > 1]
    assert len(multi) >= 10 and len({r["student_id"] for r in recs if r["student_id"]}) == len([r for r in recs if r["student_id"]])

    step("Review page shows table, REVIEW/OTHER CLASS/UNKNOWN rows")
    h = t1.get("/teacher/attendance/%d/review" % sid).get_data(as_text=True)
    for tok in ("REVIEW", "OTHER", "UNKNOWN", man["review_student"], usn(65), "FINALIZE"):
        assert tok in h.upper() or tok in h, tok
    r = t1.get("/teacher/attendance/%d/other-class" % sid).get_data(as_text=True); assert usn(65) in r and usn(66) in r

    step("Finalize is blocked while a REVIEW row is undecided")
    r = t1.post("/teacher/attendance/%d/review/save" % sid, data={"finalize": "1"})
    assert sqlite3.connect(db_path).execute("SELECT status FROM attendance_sessions WHERE id=?", (sid,)).fetchone()[0] == "review"

    step("Teacher decides REVIEW student = PRESENT, marks one undetected student present manually, finalizes")
    rev = [r for r in recs if r["ai_result"] == "REVIEW"][0]
    manual_student = 40
    sid_manual = sqlite3.connect(db_path).execute("SELECT id FROM students WHERE usn=?", (usn(manual_student),)).fetchone()[0]
    form = {"finalize": "1", "dec_%d" % rev["id"]: "PRESENT", "man_%d" % sid_manual: "PRESENT"}
    for r in recs:
        if r["ai_result"] == "PRESENT": form["dec_%d" % r["id"]] = "PRESENT"
    r = t1.post("/teacher/attendance/%d/review/save" % sid, data=form); assert r.status_code == 302 and "reports" in r.headers["Location"]

    step("Verify attendance maths: Absent = eligible roster - teacher-confirmed present")
    recs = records(db_path, sid)
    fin = {}
    for r in recs: fin.setdefault(r["final_status"], []).append(r)
    present = {r["usn"] for r in fin.get("PRESENT", [])}; absent = {r["usn"] for r in fin.get("ABSENT", [])}
    print("      FINAL: present=%d absent=%d other_class=%d unknown=%d" % (len(present), len(absent), len(fin.get("OTHER_CLASS", [])), len(fin.get("UNKNOWN", []))))
    assert len(present) == 16 and len(absent) == 64 - 16 and not (present & absent)          # 15 recognised + 1 manual
    assert usn(manual_student) in present and man["review_student"] in present
    assert all(int(u[-3:]) <= 64 for u in present | absent)                                  # roster is Section A only
    assert not ({r["usn"] for r in fin.get("OTHER_CLASS", [])} & absent)                     # OTHER CLASS never absent
    assert {r["usn"] for r in fin.get("OTHER_CLASS", [])} == set(enrolled_B)
    assert len(fin.get("UNKNOWN", [])) == 2 and all(r["student_id"] is None for r in fin["UNKNOWN"])   # UNKNOWN never absent

    step("Attendance PDF + Other-Class PDF generated, valid, and contain the right content")
    pa = t1.get("/teacher/files/report/%d/attendance.pdf" % sid); po = t1.get("/teacher/files/report/%d/other_class.pdf" % sid)
    assert pa.status_code == po.status_code == 200 and pa.mimetype == po.mimetype == "application/pdf"
    assert pa.data[:5] == po.data[:5] == b"%PDF-"
    A, O = os.path.join(d, "a.pdf"), os.path.join(d, "o.pdf"); open(A, "wb").write(pa.data); open(O, "wb").write(po.data)
    ta, to = pdf_text(A), pdf_text(O)
    for tok in ("Sai Vidya Institute of Technology", "SMART ATTENDANCE SYSTEM", "DAILY ATTENDANCE REPORT", "Data Science", "Total Eligible", usn(1), usn(64)):
        assert tok in ta, tok
    assert usn(65) not in ta.split("Classroom Evidence")[0]                                   # Section B is not in the Section A roster table
    for tok in ("OTHER-CLASS DETECTION REPORT", usn(65), usn(66), usn(67), "Student 065", "Confidence", "Timestamp", "Actual Enrollment Group", "Cloud Computing"):
        assert tok in to or tok.upper() in to.upper(), tok
    pages = lambda p: int(subprocess.run(["pdfinfo", p], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    print("      attendance.pdf: %d bytes, %d pages | other_class.pdf: %d bytes, %d pages" % (len(pa.data), pages(A), len(po.data), pages(O)))
    shutil.copy(A, "/tmp/final_attendance.pdf"); shutil.copy(O, "/tmp/final_other_class.pdf")
    assert t1.get("/teacher/files/report/%d/attendance.pdf" % sid + "?dl=1").headers["Content-Disposition"].startswith("attachment")
    assert t2.get("/teacher/files/report/%d/attendance.pdf" % sid).status_code == 404       # other teacher cannot fetch

    step("Finalized sessions are locked")
    assert t1.post("/teacher/attendance/%d/review/save" % sid, data={}).status_code == 400
    before = sorted((r["usn"] or "", r["final_status"]) for r in records(db_path, sid))
    assert t1.post("/teacher/attendance/%d/process" % sid).status_code == 409                # cannot re-run AI on a finalized session
    assert t1.post("/teacher/attendance/%d/upload" % sid, data={"photos": [(io.BytesIO(b"x"), "e.jpg")]}, content_type="multipart/form-data").status_code == 302
    assert sqlite3.connect(db_path).execute("SELECT status FROM attendance_sessions WHERE id=?", (sid,)).fetchone()[0] == "finalized"
    assert sorted((r["usn"] or "", r["final_status"]) for r in records(db_path, sid)) == before   # final attendance untouched

    step("Elective A+B session (Cloud Computing): same photos, Section B students are now ELIGIBLE (no other-class)")
    r = t1.post("/teacher/classes/start", data={"assignment_id": 2}); sid2 = int(r.headers["Location"].rsplit("/", 1)[1])
    upload_and_process(t1, sid2)
    rec2 = records(db_path, sid2)
    ok2 = {r["usn"] for r in rec2 if r["ai_result"] in ("PRESENT", "REVIEW")}
    assert ok2 == set(enrolled_A) | set(enrolled_B) and not [r for r in rec2 if r["ai_result"] == "OTHER_CLASS"]
    assert len([r for r in rec2 if r["ai_result"] == "UNKNOWN"]) == 2

    step("Persistence: brand-new app instance (restart) on the same data directory")
    app2 = create_app(cfg); c2 = app2.test_client()
    assert login(c2, "teacher", "teacher.demo@college.edu", "Demo@12345").status_code == 302
    h = c2.get("/teacher/reports").get_data(as_text=True); assert "Data Science" in h
    assert c2.get("/teacher/files/report/%d/attendance.pdf" % sid).data[:5] == b"%PDF-"
    n = sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM students").fetchone()[0]; assert n == 129     # 128 + the one we added
    assert sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM face_profiles").fetchone()[0] == 18       # seed did not duplicate
    print("      ALL ACCEPTANCE STEPS PASSED")

def test_threshold_logic_unit():
    from app import ai
    assert ai.classify(0.74, 0.20) == "PRESENT"
    assert ai.classify(0.74, 0.70) == "REVIEW"      # ambiguous between two people -> never auto-present
    assert ai.classify(0.42, 0.10) == "REVIEW"
    assert ai.classify(0.20, 0.05) == "UNKNOWN"
