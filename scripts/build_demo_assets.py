"""Build the controlled DEMO face assets (NOT committed to git).

Source: LFW (Labeled Faces in the Wild) via a public GitHub mirror, cloned at build time.
Creates:
  demo_assets/gallery/<USN>/g1..g3.jpg       enrolment photos
  demo_assets/classroom/classroom_01..04.jpg composite 'classroom' scenes (same identities, DIFFERENT photos)
  demo_assets/manifest.json             validation only (tests), written AFTER composition; the app never reads it
LFW photos are research-use data: fetched at build time, never redistributed in this repo.
"""
import os, sys, glob, json, random, subprocess, shutil
import numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import ai

OUT = os.path.join(ROOT, "demo_assets")
LFW = os.environ.get("LFW_DIR") or os.path.join(OUT, "_lfw")   # private/local LFW copy (never committed)
MIRROR = "https://github.com/redwankarimsony/deepfunneled_lfw.git"
rng = random.Random(7)

def usn(n): return f"01DEMO23DS{n:03d}"

ENROLLED = list(range(1, 16)) + [65, 66, 67]                 # students with a face profile (A: 001-015, B: 065-067)
PHOTOS = {                                                    # classroom composition ("S1"/"S2" = never-enrolled strangers)
 1: list(range(1, 9)) + [65, "S1"],
 2: list(range(5, 13)) + [66],
 3: list(range(9, 16)) + [67],
 4: [13, 14, 15, 1, 2, 4, 5, 65, "S2"],
}
REVIEW_STUDENT = 3
DEGRADE_SCALE = float(os.environ.get("DEGRADE_SCALE", "0.38"))
DEGRADE_BLUR = float(os.environ.get("DEGRADE_BLUR", "1.6"))

def fetch_lfw():
    if os.path.isdir(LFW) and os.listdir(LFW): return
    os.makedirs(OUT, exist_ok=True)
    subprocess.check_call(["git", "clone", "--depth", "1", "-q", MIRROR, LFW])

def best_face_emb(path):
    img = cv2.imread(path)
    fs = []
    for sz in (320, 480):
        fs = ai.detect(img, size=sz) if img is not None else []
        if fs: break
    return max(fs, key=lambda f: f["score"])["emb"] if fs else None

def main():
    fetch_lfw()
    ids = {d: sorted(glob.glob(f"{LFW}/{d}/*.jpg")) for d in sorted(os.listdir(LFW))
           if os.path.isdir(f"{LFW}/{d}") and not d.startswith(".")}
    cands = [d for d, f in ids.items() if len(f) >= 6]
    rng.shuffle(cands)
    need = len(ENROLLED) + 2
    chosen, info = [], {}
    cache = os.path.join(OUT, "_cand_cache.json")          # private/local speed-up, git-ignored
    if os.path.exists(cache):
        c = json.load(open(cache)); chosen = c["chosen"]; info = {d: {"rest": [tuple(x) for x in v["rest"]]} for d, v in c["info"].items()}
        cands = []
    for d in cands:
        embs = [best_face_emb(p) for p in ids[d][:6]]
        if any(e is None for e in embs): continue
        info[d] = {"rest": sorted([(float(max(embs[j] @ embs[i] for j in range(3))), i) for i in range(3, 6)], reverse=True)}
        chosen.append(d); print("cand", len(chosen), d, flush=True)
        if len(chosen) >= need + 22: break
    json.dump({"chosen": chosen, "info": {d: v for d, v in info.items()}}, open(cache, "w"))
    strong = [d for d in chosen if info[d]["rest"][0][0] >= 0.62]
    assert len(strong) >= need, len(strong)
    pool = list(strong)
    who = {n: pool.pop(0) for n in ENROLLED}      # REVIEW_STUDENT is a normal identity; their classroom face is degraded in compose()
    who["S1"], who["S2"] = pool.pop(0), pool.pop(0)

    shutil.rmtree(os.path.join(OUT, "gallery"), ignore_errors=True)
    classroom_face = {}
    for key, d in who.items():
        if isinstance(key, int):
            gd = os.path.join(OUT, "gallery", usn(key)); os.makedirs(gd, exist_ok=True)
            for k in range(3):
                shutil.copy(ids[d][k], os.path.join(gd, f"g{k+1}.jpg"))
        sim, i = info[d]["rest"][0]
        classroom_face[key] = (ids[d][i], sim)
    os.makedirs(os.path.join(OUT, "classroom"), exist_ok=True)
    truth = {}
    for pno, members in PHOTOS.items():
        cv2.imwrite(os.path.join(OUT, "classroom", f"classroom_{pno:02d}.jpg"),
                    compose(members, classroom_face, pno), [cv2.IMWRITE_JPEG_QUALITY, 93])
        truth[f"classroom_{pno:02d}.jpg"] = [usn(m) if isinstance(m, int) else m for m in members]
    json.dump({"photos": truth, "review_student": usn(REVIEW_STUDENT), "source": "LFW via " + MIRROR},
              open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print("built; review identity classroom-vs-gallery sim=%.2f" % classroom_face[REVIEW_STUDENT][1])

def compose(members, classroom_face, seed):
    """Synthetic 'classroom photo': out-of-focus room, 3 staggered depth rows, desks overlapping bodies, vignette + sensor noise.
    Deterministic (seeded). Faces are LFW photos of the SAME identities as the gallery but DIFFERENT photographs."""
    r = random.Random(seed * 101)
    W, H = 1600, 1066
    img = np.zeros((H, W, 3), np.float32)
    for y in range(H):
        t = y / H
        img[y, :] = (196 - 40 * t, 206 - 48 * t, 214 - 52 * t)
    cv2.rectangle(img, (0, int(H * .70)), (W, H), (118, 132, 148), -1)
    for x in (90, 600, 1110):
        cv2.rectangle(img, (x, 50), (x + 400, 330), (240, 236, 228), -1)
        for k in (1, 2): cv2.line(img, (x + k * 133, 50), (x + k * 133, 330), (190, 190, 190), 6)
    cv2.rectangle(img, (520, 360), (1080, 470), (60, 86, 58), -1)
    cv2.rectangle(img, (520, 360), (1080, 470), (140, 150, 160), 8)
    img = np.clip(cv2.GaussianBlur(img, (0, 0), 7), 0, 255).astype(np.uint8)       # background out of focus

    n = len(members); k0 = n // 3; k1 = n // 3
    rows = [members[:k0], members[k0:k0 + k1], members[k0 + k1:]]
    cfg = [(480, .78, 30), (700, .98, 55), (930, 1.22, -35)]                     # (face centre y, scale, x shift): back/middle/front
    shirts = [(180, 90, 60), (60, 120, 170), (90, 90, 90), (70, 150, 90), (140, 80, 150), (50, 60, 160), (40, 40, 40), (200, 200, 205)]
    for row, (cy, sc, shift) in zip(rows, cfg):
        cell = W / max(1, len(row))
        for j, m in enumerate(row):
            f = cv2.imread(classroom_face[m][0])
            c = f[25:225, 35:215]
            c = cv2.resize(c, None, fx=sc * 1.25 * r.uniform(.95, 1.08), fy=sc * 1.25 * r.uniform(.95, 1.08), interpolation=cv2.INTER_CUBIC)
            if m == REVIEW_STUDENT:     # back-row, poorly lit, small face -> genuinely lower recognition confidence
                c = cv2.resize(c, None, fx=DEGRADE_SCALE, fy=DEGRADE_SCALE, interpolation=cv2.INTER_AREA)
                c = cv2.GaussianBlur(c, (0, 0), DEGRADE_BLUR); c = (c.astype(np.float32) * 0.62).astype(np.uint8)
            h, w = c.shape[:2]
            cx = int(cell * (j + .5) + shift + r.randint(-30, 30)); cx = max(w // 2, min(W - w // 2, cx))
            x0 = cx - w // 2; y0 = max(0, min(H - h, cy - h // 2 + r.randint(-18, 18)))
            col = shirts[r.randrange(len(shirts))]
            sh_y = y0 + h - int(.05 * h)
            cv2.ellipse(img, (cx, sh_y + int(.55 * h)), (int(w * .95), int(h * .62)), 0, 180, 360, col, -1)
            cv2.rectangle(img, (cx - int(w * .95), sh_y + int(.55 * h)), (cx + int(w * .95), H), col, -1)
            neck = tuple(int(v) for v in c[int(h * .85):int(h * .95), int(w * .35):int(w * .65)].reshape(-1, 3).mean(0) * .9)
            cv2.rectangle(img, (cx - int(w * .13), y0 + int(h * .78)), (cx + int(w * .13), sh_y + int(.12 * h)), neck, -1)
            mask = np.zeros((h, w), np.float32)
            cv2.ellipse(mask, (w // 2, h // 2), (int(w * .46), int(h * .49)), 0, 0, 360, 1, -1)
            mask = cv2.GaussianBlur(mask, (0, 0), 7)[..., None]
            roi = img[y0:y0 + h, x0:x0 + w].astype(np.float32)
            img[y0:y0 + h, x0:x0 + w] = (roi * (1 - mask) + c.astype(np.float32) * mask).astype(np.uint8)
        desk_y = cy + int(150 * sc)                                                # desk edge overlaps the row's bodies
        cv2.rectangle(img, (0, desk_y), (W, desk_y + int(55 * sc) + 20), (82, 112, 150), -1)
        cv2.rectangle(img, (0, desk_y), (W, desk_y + 8), (60, 85, 120), -1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - .28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    out = img.astype(np.float32) * vig[..., None] + np.random.RandomState(seed).normal(0, 3.5, img.shape)
    return cv2.GaussianBlur(np.clip(out, 0, 255).astype(np.uint8), (0, 0), 0.7)

if __name__ == "__main__":
    main()
