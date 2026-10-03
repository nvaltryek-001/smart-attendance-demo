"""Seed the DEMO database (synthetic students only). Idempotent."""
from werkzeug.security import generate_password_hash
from .db import connect
from . import enroll

def seed(app, with_faces=True):
    db = connect(app.config["DB_PATH"])
    if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        db.execute("INSERT INTO departments(id,code,name) VALUES(1,'CSE-DS','CSE – Data Science')")
        db.execute("INSERT INTO semesters(id,number) VALUES(7,7)")
        db.execute("INSERT INTO sections(id,name,department_id,semester_id) VALUES(1,'A',1,7),(2,'B',1,7)")
        for n in range(1, 129):
            db.execute("INSERT INTO students(usn,name,department_id,semester_id,section_id) VALUES(?,?,?,?,?)",
                       ("01DEMO23DS%03d" % n, "Student %03d" % n, 1, 7, 1 if n <= 64 else 2))
        db.execute("INSERT INTO users(id,email,password_hash,role,full_name) VALUES(1,'admin.demo@college.edu',?,'admin','Demo Admin')", (generate_password_hash("Admin@12345"),))
        db.execute("INSERT INTO users(id,email,password_hash,role,full_name) VALUES(2,'teacher.demo@college.edu',?,'teacher','Prof. Demo Teacher')", (generate_password_hash("Demo@12345"),))
        db.execute("INSERT INTO teachers(id,user_id,department_id,designation) VALUES(1,2,1,'Assistant Professor')")
        db.execute("INSERT INTO subjects(id,code,name,department_id,semester_id,kind) VALUES(1,'DEMO-DS701','Data Science',1,7,'core'),(2,'DEMO-CC702','Cloud Computing',1,7,'elective')")
        db.execute("INSERT INTO subject_groups(id,subject_id,name,label) VALUES(1,1,'Data Science – Section A','Section A'),(2,2,'Cloud Computing – A+B Elective','A+B')")
        db.execute("INSERT INTO subject_group_students SELECT 1, id FROM students WHERE section_id=1")
        db.execute("INSERT INTO subject_group_students SELECT 2, id FROM students WHERE usn BETWEEN '01DEMO23DS001' AND '01DEMO23DS032' OR usn BETWEEN '01DEMO23DS065' AND '01DEMO23DS096'")
        db.execute("INSERT INTO teacher_assignments(id,teacher_id,subject_id,group_id) VALUES(1,1,1,1),(2,1,2,2)")
        for wd in range(7):   # demo: every weekday so 'Today's classes' is never empty during a live demo
            db.execute("INSERT INTO timetable(assignment_id,weekday,hour_no,start_time,end_time) VALUES(1,?,1,'09:00','10:00'),(2,?,5,'13:30','14:30')", (wd, wd))
        db.commit()
    n = 0
    if with_faces: n = enroll.enroll_demo_gallery(db, app.config["ASSET_DIR"])
    db.close(); return n

