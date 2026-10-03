import os, json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from .db import now

COLLEGE = "Sai Vidya Institute of Technology"
NAVY = colors.HexColor("#14213d")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=17, textColor=NAVY, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, textColor=NAVY, spaceBefore=8)
SM = ParagraphStyle("sm", parent=ss["Normal"], fontSize=8.5, textColor=colors.HexColor("#555555"))
CELL = ParagraphStyle("c", parent=ss["Normal"], fontSize=8.5, leading=10)

def _session_ctx(db, sid):
    s = db.execute("""SELECT s.*, sub.name subject, sub.code scode, g.name gname, g.label glabel, u.full_name faculty,
                      d.name dept, sem.number semester
                      FROM attendance_sessions s JOIN subjects sub ON sub.id=s.subject_id JOIN subject_groups g ON g.id=s.group_id
                      JOIN teachers t ON t.id=s.teacher_id JOIN users u ON u.id=t.user_id
                      JOIN departments d ON d.id=sub.department_id JOIN semesters sem ON sem.id=sub.semester_id
                      WHERE s.id=?""", (sid,)).fetchone()
    return s

def _header(story, title, s):
    story += [Paragraph(COLLEGE, H1), Paragraph("SMART ATTENDANCE SYSTEM", ParagraphStyle("x", parent=H2, alignment=1, spaceBefore=0)),
              Paragraph(title, ParagraphStyle("t", parent=H2, alignment=1, spaceBefore=0, fontSize=13)),
              Paragraph("<font color='#b00020'><b>DEMO MODE</b> — synthetic demo students; not real attendance data</font>",
                        ParagraphStyle("d", parent=SM, alignment=1)), Spacer(1, 6)]
    story[0].style.alignment = 1

def _meta(story, s):
    rows = [["Date", s["session_date"], "Department", s["dept"]],
            ["Semester", "%s" % s["semester"], "Section / Group", s["glabel"]],
            ["Subject", s["subject"], "Faculty", s["faculty"]],
            ["Hour", str(s["hour_no"] or "-"), "Time", "%s – %s" % (s["start_time"] or "-", s["end_time"] or "-")]]
    t = Table(rows, colWidths=[24*mm, 58*mm, 32*mm, 58*mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                           ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), .4, colors.grey),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f6")), ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef1f6"))]))
    story += [t, Spacer(1, 8)]

def _foot(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.grey)
    canvas.drawString(15*mm, 10*mm, "%s · Smart Attendance System · DEMO MODE · generated %s" % (COLLEGE, now()))
    canvas.drawRightString(195*mm, 10*mm, "Page %d" % doc.page); canvas.restoreState()

def _fit_image(path, maxw, maxh):
    from PIL import Image as PI
    w, h = PI.open(path).size; k = min(maxw / w, maxh / h)
    return Image(path, w * k, h * k)

def attendance_pdf(db, data_dir, sid):
    s = _session_ctx(db, sid)
    roster = db.execute("""SELECT st.id, st.usn, st.name, sec.name sec FROM subject_group_students sg
                           JOIN students st ON st.id=sg.student_id JOIN sections sec ON sec.id=st.section_id
                           WHERE sg.group_id=? ORDER BY st.usn""", (s["group_id"],)).fetchall()
    fin = {r["student_id"]: r["final_status"] for r in db.execute(
        "SELECT student_id, final_status FROM attendance_records WHERE session_id=? AND student_id IS NOT NULL", (sid,))}
    cnt = lambda k: db.execute("SELECT COUNT(*) FROM attendance_records WHERE session_id=? AND ai_result=?", (sid, k)).fetchone()[0]
    present = sum(1 for r in roster if fin.get(r["id"]) == "PRESENT")
    story = []; _header(story, "DAILY ATTENDANCE REPORT", s); _meta(story, s)
    data = [["Sl No", "USN", "Name", "Section", "Status"]]
    st_col = []
    for i, r in enumerate(roster, 1):
        st = "PRESENT" if fin.get(r["id"]) == "PRESENT" else "ABSENT"
        data.append([str(i), r["usn"], r["name"], r["sec"], st])
        if st == "ABSENT": st_col.append(("TEXTCOLOR", (4, i), (4, i), colors.HexColor("#b00020")))
        else: st_col.append(("TEXTCOLOR", (4, i), (4, i), colors.HexColor("#1b7a2f")))
    t = Table(data, colWidths=[14*mm, 40*mm, 50*mm, 22*mm, 28*mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), .3, colors.lightgrey),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]), ("FONTNAME", (4, 1), (4, -1), "Helvetica-Bold")] + st_col))
    summ = [["Total Eligible", len(roster)], ["Present", present], ["Absent", len(roster) - present],
            ["Review (flagged by AI)", cnt("REVIEW")], ["Other Class (not counted)", cnt("OTHER_CLASS")], ["Unknown faces", cnt("UNKNOWN")]]
    st2 = Table(summ, colWidths=[60*mm, 25*mm])
    st2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .4, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9),
                             ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f6")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    story += [Paragraph("Summary", H2), st2, Spacer(1, 4),
              Paragraph("Absent = eligible roster minus teacher-confirmed present. Unknown and Other-Class faces are never counted as absent.", SM),
              Paragraph("Attendance Register", H2), t]
    photos = db.execute("SELECT * FROM attendance_photos WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    if photos:
        story += [PageBreak(), Paragraph("Classroom Evidence Photos", H2),
                  Paragraph("Boxes: green = present candidate, yellow = review, orange = other class, grey = unknown.", SM)]
        for p in photos:
            path = p["annotated_path"] or p["path"]
            if os.path.exists(path):
                story += [KeepTogether([Paragraph("%s — %s faces detected" % (p["filename"], p["faces_detected"]), SM),
                                        _fit_image(path, 170*mm, 85*mm), Spacer(1, 6)])]
    out = os.path.join(data_dir, "reports"); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "attendance_session_%d.pdf" % sid)
    SimpleDocTemplate(path, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=14*mm, bottomMargin=16*mm,
                      title="Daily Attendance Report").build(story, onFirstPage=_foot, onLaterPages=_foot)
    _save(db, sid, "attendance", path); return path

def other_class_pdf(db, data_dir, sid):
    s = _session_ctx(db, sid)
    rows = db.execute("""SELECT o.*, st.name, st.usn, sec.name sec, sem.number semester, d.name dept, r.crop_path, r.photo_id
                         FROM other_class_detections o JOIN students st ON st.id=o.student_id JOIN sections sec ON sec.id=st.section_id
                         JOIN semesters sem ON sem.id=st.semester_id JOIN departments d ON d.id=st.department_id
                         LEFT JOIN attendance_records r ON r.id=o.record_id WHERE o.session_id=? ORDER BY st.usn""", (sid,)).fetchall()
    story = []; _header(story, "OTHER-CLASS DETECTION REPORT", s); _meta(story, s)
    story.append(Paragraph("Students recognised in the classroom who are <b>not enrolled</b> in the current subject. "
                           "They are not counted absent and not counted present for this subject.", SM))
    if not rows: story.append(Paragraph("No other-class students were detected in this session.", ss["Normal"]))
    for o in rows:
        groups = db.execute("""SELECT sub.name||' ('||g.label||')' n FROM subject_group_students sg JOIN subject_groups g ON g.id=sg.group_id
                               JOIN subjects sub ON sub.id=g.subject_id WHERE sg.student_id=?""", (o["student_id"],)).fetchall()
        actual = "Section %s, Sem %s" % (o["sec"], o["semester"]) + ("; " + ", ".join(x["n"] for x in groups) if groups else "")
        info = [["Student Name", o["name"]], ["USN", o["usn"]], ["Department", o["dept"]], ["Semester", str(o["semester"])],
                ["Section", o["sec"]], ["Current Subject", "%s (%s)" % (s["subject"], s["glabel"])],
                ["Actual Enrollment Group", Paragraph(actual, CELL)], ["Confidence", "%.0f%%" % o["confidence"]],
                ["Timestamp", o["detected_at"]]]
        t = Table(info, colWidths=[40*mm, 70*mm])
        t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), .3, colors.grey),
                               ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff2e0"))]))
        img = _fit_image(o["crop_path"], 40*mm, 40*mm) if o["crop_path"] and os.path.exists(o["crop_path"]) else ""
        card = Table([[t, img]], colWidths=[115*mm, 50*mm]); card.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story += [Spacer(1, 8), KeepTogether([Paragraph("Evidence face crop", SM), card])]
        p = db.execute("SELECT * FROM attendance_photos WHERE id=?", (o["photo_id"],)).fetchone()
        if p and p["annotated_path"] and os.path.exists(p["annotated_path"]):
            story += [Paragraph("Evidence photo: %s" % p["filename"], SM), _fit_image(p["annotated_path"], 150*mm, 70*mm)]
    out = os.path.join(data_dir, "reports"); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "other_class_session_%d.pdf" % sid)
    SimpleDocTemplate(path, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=14*mm, bottomMargin=16*mm,
                      title="Other-Class Detection Report").build(story, onFirstPage=_foot, onLaterPages=_foot)
    _save(db, sid, "other_class", path); return path

def _save(db, sid, kind, path):
    db.execute("DELETE FROM attendance_reports WHERE session_id=? AND kind=?", (sid, kind))
    db.execute("INSERT INTO attendance_reports(session_id,kind,path,created_at) VALUES(?,?,?,?)", (sid, kind, path, now())); db.commit()
