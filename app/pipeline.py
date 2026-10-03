"""Attendance recognition pipeline. Everything here is computed from the uploaded photos."""
import os, json, threading, traceback
import numpy as np, cv2
from . import ai
from .db import connect, now

STAGES = ["Uploading photos", "Checking image quality", "Detecting faces", "Extracting face embeddings",
          "Matching students", "Removing duplicate detections", "Checking subject enrollment",
          "Calculating attendance", "Preparing teacher review"]
COLORS = {"PRESENT": (80, 175, 40), "REVIEW": (0, 200, 240), "OTHER_CLASS": (0, 140, 255), "UNKNOWN": (170, 170, 170)}

def set_stage(db, sid, n, msg=None, status=None):
    db.execute("UPDATE attendance_sessions SET stage=?, stage_msg=?, status=COALESCE(?,status) WHERE id=?",
               (n, msg or STAGES[n - 1], status, sid)); db.commit()

def load_gallery(db):
    rows = db.execute("""SELECT fp.student_id sid, fe.embedding FROM face_embeddings fe
                         JOIN face_profiles fp ON fp.id=fe.profile_id WHERE fp.status='enrolled'""").fetchall()
    if not rows: return None, []
    return (np.stack([np.frombuffer(r["embedding"], np.float32) for r in rows]), [r["sid"] for r in rows])

def start_async(app, session_id):
    t = threading.Thread(target=_safe_run, args=(app, session_id), daemon=True)
    t.start(); return t

def _safe_run(app, session_id):
    db = connect(app.config["DB_PATH"])
    try:
        run(db, app.config["DATA_DIR"], session_id)
    except Exception as e:
        traceback.print_exc()
        db.execute("UPDATE attendance_sessions SET status='failed', error=? WHERE id=?", (str(e)[:300], session_id)); db.commit()
    finally:
        db.close()

def run(db, data_dir, sid):
    sess = db.execute("SELECT * FROM attendance_sessions WHERE id=?", (sid,)).fetchone()
    photos = db.execute("SELECT * FROM attendance_photos WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    sdir = os.path.join(data_dir, "sessions", str(sid)); os.makedirs(os.path.join(sdir, "crops"), exist_ok=True)
    db.execute("DELETE FROM attendance_records WHERE session_id=?", (sid,))
    db.execute("DELETE FROM other_class_detections WHERE session_id=?", (sid,)); db.commit()
    set_stage(db, sid, 1, "Uploading photos — %d received" % len(photos), "processing")

    # 2 quality
    set_stage(db, sid, 2)
    imgs = {}
    for p in photos:
        img = ai.read_image(p["path"]); imgs[p["id"]] = img
        qa = ai.image_quality(img)
        db.execute("UPDATE attendance_photos SET width=?,height=?,blur=?,quality_ok=? WHERE id=?",
                   (qa["width"], qa["height"], qa["blur"], int(qa["ok"]), p["id"]))
    db.commit()

    # 3 detect
    set_stage(db, sid, 3)
    det = {}
    for i, p in enumerate(photos, 1):
        set_stage(db, sid, 3, "Detecting faces — photo %d of %d" % (i, len(photos)))
        det[p["id"]] = ai.detect_boxes(imgs[p["id"]])
        db.execute("UPDATE attendance_photos SET faces_detected=? WHERE id=?", (len(det[p["id"]]), p["id"]))
    db.commit()

    # 4 embeddings
    faces = []   # dicts with photo_id,bbox,score,emb
    for i, p in enumerate(photos, 1):
        set_stage(db, sid, 4, "Extracting face embeddings — photo %d of %d" % (i, len(photos)))
        for f in ai.embed_faces(imgs[p["id"]], det[p["id"]]):
            f["photo_id"] = p["id"]; faces.append(f)

    # 5 match against full face gallery (all enrolled students, not only this class)
    set_stage(db, sid, 5)
    gmat, gids = load_gallery(db)
    for f in faces:
        f["sid"], f["sim"], f["second"] = ai.match(f["emb"], gmat, gids)
        f["cls"] = ai.classify(f["sim"], f["second"])

    # 6 dedup across photos
    set_stage(db, sid, 6)
    removed = 0
    by_student, unknowns = {}, []
    for f in faces:
        if f["cls"] in ("PRESENT", "REVIEW"):
            by_student.setdefault(f["sid"], []).append(f)
        else:
            unknowns.append(f)
    kept = []
    for st, lst in by_student.items():
        lst.sort(key=lambda x: -x["sim"])
        best = lst[0]; best["seen"] = len({x["photo_id"] for x in lst})
        removed += len(lst) - 1
        # if any sighting is strong, the student's class is the strongest sighting's class
        kept.append(best)
    clusters = []
    for f in sorted(unknowns, key=lambda x: -x["score"]):
        for c in clusters:
            if float(c["emb"] @ f["emb"]) >= ai.T_DEDUP_UNKNOWN:
                c["_photos"].add(f["photo_id"]); removed += 1; break
        else:
            f["_photos"] = {f["photo_id"]}; clusters.append(f)
    for c in clusters: c["seen"] = len(c["_photos"]); kept.append(c)

    # 7 subject eligibility
    set_stage(db, sid, 7)
    roster = {r["student_id"] for r in db.execute(
        "SELECT student_id FROM subject_group_students WHERE group_id=?", (sess["group_id"],))}
    results = []
    for f in kept:
        if f["cls"] in ("PRESENT", "REVIEW"):
            if f["sid"] in roster:
                f["result"] = f["cls"]; f["student"] = f["sid"]
            elif f["cls"] == "PRESENT":
                f["result"] = "OTHER_CLASS"; f["student"] = f["sid"]   # recognised, valid student, not in this subject
            else:
                f["result"] = "UNKNOWN"; f["student"] = None           # weak match to a non-roster student: do not accuse
        else:
            f["result"] = "UNKNOWN"; f["student"] = None
        results.append(f)

    # 8 persist (attendance NOT finalised: absent is only computed at finalize)
    set_stage(db, sid, 8)
    ann = {p["id"]: imgs[p["id"]].copy() for p in photos}
    results.sort(key=lambda f: (f["photo_id"], f["bbox"][0]))
    for f in results:
        x1, y1, x2, y2 = [int(v) for v in f["bbox"]]
        im = imgs[f["photo_id"]]; h, w = im.shape[:2]
        bw, bh = x2 - x1, y2 - y1
        cx1, cy1, cx2, cy2 = max(0, x1 - bw // 4), max(0, y1 - bh // 4), min(w, x2 + bw // 4), min(h, y2 + bh // 4)
        crop = cv2.resize(im[cy1:cy2, cx1:cx2], (160, 160))
        cp = os.path.join(sdir, "crops", "f%d_%d.jpg" % (f["photo_id"], x1)); cv2.imwrite(cp, crop)
        conf = ai.sim_to_conf(f["sim"])
        dec = "PRESENT" if f["result"] == "PRESENT" else None
        cur = db.execute("""INSERT INTO attendance_records(session_id,student_id,ai_result,confidence,similarity,photo_id,bbox,
                            crop_path,seen_in_photos,teacher_decision) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                         (sid, f["student"], f["result"], conf, f["sim"], f["photo_id"], json.dumps([x1, y1, x2, y2]),
                          cp, f["seen"], dec))
        if f["result"] == "OTHER_CLASS":
            db.execute("INSERT INTO other_class_detections(session_id,record_id,student_id,confidence,photo_id,detected_at) VALUES(?,?,?,?,?,?)",
                       (sid, cur.lastrowid, f["student"], conf, f["photo_id"], now()))
        col = COLORS[f["result"]]
        cv2.rectangle(ann[f["photo_id"]], (x1, y1), (x2, y2), col, 4)
    for p in photos:
        ap = os.path.join(sdir, "annotated_%d.jpg" % p["id"]); cv2.imwrite(ap, ann[p["id"]], [cv2.IMWRITE_JPEG_QUALITY, 88])
        db.execute("UPDATE attendance_photos SET annotated_path=? WHERE id=?", (ap, p["id"]))
    db.commit()

    # 9 ready
    summary = "%d faces found, %d unique people, %d duplicate sightings removed" % (len(faces), len(results), removed)
    db.execute("UPDATE attendance_sessions SET stage=9, stage_msg=?, status='review', error=NULL WHERE id=?",
               ("Prepared for teacher review — " + summary, sid)); db.commit()
