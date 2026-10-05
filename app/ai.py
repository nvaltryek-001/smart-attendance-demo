"""Face engine: SCRFD detection + ArcFace embeddings (InsightFace) on ONNX Runtime + OpenCV."""
import os, threading
import numpy as np, cv2

MODEL_NAME = os.environ.get("FACE_MODEL", "buffalo_sc")
DET_SIZE = int(os.environ.get("DET_SIZE", "320"))

# similarity thresholds (cosine on L2-normalised ArcFace embeddings)
T_PRESENT = float(os.environ.get("T_PRESENT", "0.50"))
T_REVIEW = float(os.environ.get("T_REVIEW", "0.35"))
T_MARGIN = 0.08          # top1 - top2 must exceed this for an auto PRESENT
T_DEDUP_UNKNOWN = 0.45   # same stranger seen in two photos

_lock = threading.Lock()
_app = None

def engine():
    global _app
    with _lock:
        if _app is None:
            from insightface.app import FaceAnalysis
            a = FaceAnalysis(name=MODEL_NAME, providers=["CPUExecutionProvider"],
                             allowed_modules=["detection", "recognition"])
            a.prepare(ctx_id=-1, det_size=(DET_SIZE, DET_SIZE), det_thresh=0.5)
            _app = a
    return _app

def sim_to_conf(s):
    """Map cosine similarity to a human-readable 0-100 confidence (monotonic, uncalibrated)."""
    return float(100.0 / (1.0 + np.exp(-(s - 0.38) * 14.0)))

def image_quality(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(g, cv2.CV_64F).var())
    h, w = g.shape
    ok = blur > 30 and min(h, w) >= 480
    return {"blur": round(blur, 1), "width": w, "height": h, "ok": bool(ok)}

def read_image(path_or_bytes):
    if isinstance(path_or_bytes, (bytes, bytearray)):
        img = cv2.imdecode(np.frombuffer(path_or_bytes, np.uint8), cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(path_or_bytes)
    if img is None:
        raise ValueError("Unreadable image")
    h, w = img.shape[:2]
    m = max(h, w)
    if m > 2200:   # cap huge phone photos to keep CPU time sane
        s = 2200.0 / m
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img

def detect_boxes(img, size=None):
    """Stage A: SCRFD face detection only. Returns InsightFace Face objects (bbox, kps, det_score)."""
    from insightface.app.common import Face
    a = engine()
    n = size or DET_SIZE
    bboxes, kpss = a.det_model.detect(img, input_size=(n, n), max_num=0, metric="default")
    faces = []
    for i in range(bboxes.shape[0]):
        faces.append(Face(bbox=bboxes[i, 0:4], kps=kpss[i] if kpss is not None else None,
                          det_score=bboxes[i, 4]))
    return faces

def embed_faces(img, faces):
    """Stage B: ArcFace embeddings for already-detected faces."""
    rec = engine().models["recognition"]
    out = []
    for f in faces:
        rec.get(img, f)
        out.append({"bbox": [float(v) for v in f.bbox], "score": float(f.det_score),
                    "emb": f.normed_embedding.astype(np.float32)})
    return out

def detect(img, size=None):
    return embed_faces(img, detect_boxes(img, size))

def enroll_embedding(img):
    """Pick the largest face for enrolment. Raises ValueError if unusable."""
    fs = []
    for sz in (480, 320, 640):        # small enrolment photos detect best on a small canvas; try a few
        fs = detect(img, size=sz)
        if fs: break
    if not fs:
        raise ValueError("No face detected")
    f = max(fs, key=lambda d: (d["bbox"][2]-d["bbox"][0])*(d["bbox"][3]-d["bbox"][1]))
    if f["score"] < 0.6:
        raise ValueError("Face too unclear (detector score %.2f)" % f["score"])
    return f

def match(emb, gallery_mat, gallery_ids):
    """Max-sim per student. Returns (best_student_id, best_sim, second_best_sim)."""
    if gallery_mat is None or len(gallery_ids) == 0:
        return None, 0.0, 0.0
    sims = gallery_mat @ emb
    per = {}
    for sid, s in zip(gallery_ids, sims):
        if s > per.get(sid, -1):
            per[sid] = float(s)
    ranked = sorted(per.items(), key=lambda kv: -kv[1])
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    return ranked[0][0], ranked[0][1], second

def classify(sim, second):
    if sim >= T_PRESENT and (sim - second) >= T_MARGIN:
        return "PRESENT"
    if sim >= T_REVIEW:
        return "REVIEW"
    return "UNKNOWN"
