import os, glob
from . import ai
from .db import now

def enroll_images(db, student_id, images, source="upload"):
    """images: list of BGR arrays. Returns (n_ok, [errors]). Real detection + ArcFace embedding."""
    ok, errs = 0, []
    prof = db.execute("SELECT id FROM face_profiles WHERE student_id=?", (student_id,)).fetchone()
    for i, img in enumerate(images, 1):
        try:
            f = ai.enroll_embedding(img)
        except ValueError as e:
            errs.append("photo %d: %s" % (i, e)); continue
        if not prof:
            cur = db.execute("INSERT INTO face_profiles(student_id,status,enrolled_at) VALUES(?,?,?)", (student_id, "enrolled", now()))
            prof = {"id": cur.lastrowid}
        db.execute("INSERT INTO face_embeddings(profile_id,embedding,det_score,source) VALUES(?,?,?,?)",
                   (prof["id"], f["emb"].tobytes(), f["score"], source)); ok += 1
    db.commit(); return ok, errs

def enroll_demo_gallery(db, asset_dir, only_missing=True):
    import cv2
    n = 0
    for d in sorted(glob.glob(os.path.join(asset_dir, "gallery", "*"))):
        usn = os.path.basename(d)
        st = db.execute("SELECT id FROM students WHERE usn=?", (usn,)).fetchone()
        if not st: continue
        if only_missing and db.execute("SELECT 1 FROM face_profiles WHERE student_id=?", (st["id"],)).fetchone(): continue
        imgs = [cv2.imread(p) for p in sorted(glob.glob(os.path.join(d, "*.jpg")))]
        ok, _ = enroll_images(db, st["id"], [i for i in imgs if i is not None], source="demo_gallery")
        n += bool(ok)
    return n
