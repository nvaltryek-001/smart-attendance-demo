"""Render the README product-tour video (docs/demo/attendance-tour.mp4).

    python scripts/demo/render_tour_video.py
    ffmpeg -framerate 30 -i $TMP/sa_tour_frames/%05d.png -c:v libx264 -crf 22 -pix_fmt yuv420p docs/demo/attendance-tour.mp4

App screens are real screenshots from docs/screenshots/ (classroom photos blurred).
The "demo set" scene is drawn from demo_assets/manifest.json (ground truth), not from a model run.
Needs numpy + Pillow and the Inter font.
"""
import glob, json, math, os, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "docs" / "screenshots"
OUT = os.environ.get("DEMO_FRAMES_DIR", os.path.join(tempfile.gettempdir(), "sa_tour_frames"))
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(f"{OUT}/*.png"):
    os.remove(f)
W, H, FPS = 1280, 720, 30

NAVY = (19, 33, 60); NAVY2 = (28, 46, 82); CREAM = (244, 241, 234); ON = (240, 236, 226); MUTED = (160, 170, 190)
ORANGE = (224, 122, 0); RED = (176, 0, 32); GREEN = (80, 175, 40); CYAN = (0, 170, 210); AMBER = (240, 180, 40); GREY = (150, 155, 165)
FD = "/usr/share/fonts/opentype/inter/"
F = lambda s, w="SemiBold": ImageFont.truetype(f"{FD}Inter-{w}.otf", s)
FX = lambda s, w="Bold": ImageFont.truetype(f"{FD}InterDisplay-{w}.otf", s)

def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def ease_io(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def mix(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def make_bg():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    base = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        base[..., i] = NAVY[i] * (1 - 0.45 * y)
    g1 = np.exp(-(((x - 0.1) ** 2) / 0.06 + ((y - 0.12) ** 2) / 0.08))
    g2 = np.exp(-(((x - 0.95) ** 2) / 0.05 + ((y - 0.95) ** 2) / 0.07))
    base += g1[..., None] * np.array(ORANGE) * 0.28 + g2[..., None] * np.array(CYAN) * 0.18
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(grid)
    for gx in range(0, W, 48):
        d.line([(gx, 0), (gx, H)], fill=(255, 220, 180, 8))
    for gy in range(0, H, 48):
        d.line([(0, gy), (W, gy)], fill=(255, 220, 180, 8))
    img.alpha_composite(grid)
    return img
BG = make_bg()

n_frame = 0
def emit(img):
    global n_frame
    img.convert("RGB").save(f"{OUT}/{n_frame:05d}.png", compress_level=1); n_frame += 1

def fade(img, a, b):
    k = min(ease(a), ease(b))
    return img if k >= 1 else Image.blend(BG, img, k)

def logo(d, x, y, s=1.0):
    d.rounded_rectangle((x, y, x + 44 * s, y + 44 * s), int(11 * s), fill=ORANGE)
    # tiny face + check
    d.ellipse((x + 9 * s, y + 9 * s, x + 25 * s, y + 25 * s), outline=(255, 255, 255), width=int(3 * s))
    d.arc((x + 5 * s, y + 22 * s, x + 29 * s, y + 46 * s), 200, 340, fill=(255, 255, 255), width=int(3 * s))
    d.line([(x + 26 * s, y + 30 * s), (x + 31 * s, y + 35 * s), (x + 39 * s, y + 25 * s)], fill=(255, 255, 255), width=int(3 * s))

def topbar(d, tag):
    logo(d, 34, 22, 0.8)
    d.text((78, 40), "Smart College Attendance", font=F(20, "Bold"), fill=ON, anchor="lm")
    tw = d.textlength(tag, font=F(13, "Bold")) + 28
    d.rounded_rectangle((W - 36 - tw, 25, W - 36, 55), 15, fill=NAVY2, outline=ORANGE)
    d.text((W - 36 - tw / 2, 40), tag, font=F(13, "Bold"), fill=ON, anchor="mm")

# ---------- intro ----------
def intro(sec=4.0):
    for k in range(int(sec * FPS)):
        t = k / FPS; img = BG.copy(); d = ImageDraw.Draw(img)
        e = ease((t - 0.1) / 0.8)
        logo(d, W / 2 - 34, 130 - 12 * (1 - e), 1.55)
        d.text((W / 2, 250), "Smart College Attendance", font=FX(62), fill=mix(NAVY, ON, e), anchor="mm")
        e2 = ease((t - 0.5) / 0.8)
        d.text((W / 2, 315), "AI-powered classroom attendance using face recognition", font=F(26, "Medium"), fill=mix(NAVY, (255, 214, 170), e2), anchor="mm")
        e3 = ease((t - 1.1) / 0.7)
        tags = ["InsightFace", "Multi-photo merge", "Subject roster check", "Teacher review", "PDF reports"]
        tw = sum(F(15, "Bold").getlength(s) + 30 for s in tags) + 12 * 4; x = W / 2 - tw / 2
        for s in tags:
            w = F(15, "Bold").getlength(s) + 30
            d.rounded_rectangle((x, 380 + 12 * (1 - e3), x + w, 414 + 12 * (1 - e3)), 17, fill=mix(NAVY, NAVY2, e3), outline=mix(NAVY, ORANGE, e3), width=2)
            d.text((x + w / 2, 397 + 12 * (1 - e3)), s, font=F(15, "Bold"), fill=mix(NAVY, ON, e3), anchor="mm"); x += w + 12
        e4 = ease((t - 1.7) / 0.7)
        d.text((W / 2, 480), "Sai Vidya Institute of Technology  •  CSE – Data Science  •  7th Semester  •  128 demo students", font=F(17, "Medium"), fill=mix(NAVY, MUTED, e4), anchor="mm")
        # viewfinder brackets pulsing
        p = 0.5 + 0.5 * math.sin(t * 4)
        for (cx, cy, sx, sy) in [(330, 100, 1, 1), (950, 100, -1, 1), (330, 540, 1, -1), (950, 540, -1, -1)]:
            c = mix(NAVY, ORANGE, e * (0.6 + 0.4 * p))
            d.line([(cx, cy), (cx + 40 * sx, cy)], fill=c, width=4); d.line([(cx, cy), (cx, cy + 40 * sy)], fill=c, width=4)
        emit(fade(img, t / 0.35, (sec - t) / 0.35))

# ---------- workflow ----------
STEPS = [("Upload", "3–4 classroom\nphotos"), ("Detect", "find every\nface"), ("Recognise", "ArcFace embedding\nvs gallery"),
         ("Merge", "same student in\nmany photos → 1"), ("Roster", "is the student in\nthis subject?"), ("Review", "teacher confirms\nuncertain faces"),
         ("Finalize", "Attendance PDF +\nOther-Class PDF")]
def workflow(sec=6.0):
    for k in range(int(sec * FPS)):
        t = k / FPS; img = BG.copy(); d = ImageDraw.Draw(img)
        topbar(d, "HOW IT WORKS")
        d.text((W / 2, 120), "From classroom photos to a signed-off register", font=FX(40), fill=ON, anchor="mm")
        d.text((W / 2, 162), "The AI prepares the list — the teacher makes the final decision", font=F(19, "Medium"), fill=MUTED, anchor="mm")
        bw, gap = 152, 18; x0 = (W - (7 * bw + 6 * gap)) / 2; y0 = 235
        for i, (ti, sub) in enumerate(STEPS):
            e = ease((t - 0.3 - i * 0.4) / 0.5)
            x = x0 + i * (bw + gap); y = y0 + 26 * (1 - e)
            col = [ORANGE, CYAN, CYAN, CYAN, ORANGE, AMBER, GREEN][i]
            d.rounded_rectangle((x, y, x + bw, y + 210), 16, fill=mix(NAVY, NAVY2, e), outline=mix(NAVY, col, e), width=2)
            d.ellipse((x + bw / 2 - 30, y + 22, x + bw / 2 + 30, y + 82), fill=mix(NAVY, col, e))
            d.text((x + bw / 2, y + 52), str(i + 1), font=FX(28), fill=mix(NAVY, (255, 255, 255), e), anchor="mm")
            d.text((x + bw / 2, y + 112), ti, font=F(19, "Bold"), fill=mix(NAVY, ON, e), anchor="mm")
            for j, ln in enumerate(sub.split("\n")):
                d.text((x + bw / 2, y + 146 + j * 22), ln, font=F(14, "Medium"), fill=mix(NAVY, MUTED, e), anchor="mm")
            if i < 6:
                ea = ease((t - 0.55 - i * 0.4) / 0.35)
                d.line([(x + bw + 2, y0 + 105), (x + bw + 2 + (gap - 4) * ea, y0 + 105)], fill=ORANGE, width=3)
        pt = (t - 3.3) / 2.0
        if 0 <= pt <= 1:
            px = x0 + bw / 2 + ease_io(pt) * 6 * (bw + gap)
            d.ellipse((px - 9, y0 - 24, px + 9, y0 - 6), fill=AMBER)
        e = ease((t - 3.5) / 0.6)
        x = W / 2 - (4 * 200 + 3 * 20) / 2
        for s, c in [("PRESENT", GREEN), ("REVIEW", CYAN), ("OTHER CLASS", ORANGE), ("UNKNOWN", GREY)]:
            d.rounded_rectangle((x, 520, x + 200, 570), 14, fill=mix(NAVY, c, e))
            d.text((x + 100, 545), s, font=F(19, "Bold"), fill=mix(NAVY, (255, 255, 255), e), anchor="mm"); x += 220
        d.text((W / 2, 615), "Absent = on the subject roster but not seen in any photo", font=F(16, "Medium"), fill=mix(NAVY, MUTED, e), anchor="mm")
        emit(fade(img, t / 0.3, (sec - t) / 0.3))

# ---------- decision rules ----------
def rules(sec=5.0):
    rows = [("PRESENT", GREEN, "similarity ≥ 0.50  and  ≥ 0.08 ahead of the next best match", "on the roster"),
            ("REVIEW", CYAN, "similarity ≥ 0.35  (or a close second match)", "teacher decides"),
            ("OTHER CLASS", ORANGE, "confidently recognised, but not on this subject's roster", "separate PDF"),
            ("UNKNOWN", GREY, "no confident match — never accuses anyone", "not counted")]
    for k in range(int(sec * FPS)):
        t = k / FPS; img = BG.copy(); d = ImageDraw.Draw(img)
        topbar(d, "DECISION RULES")
        d.text((W / 2, 118), "How every face is classified", font=FX(40), fill=ON, anchor="mm")
        d.text((W / 2, 158), "Cosine similarity between ArcFace embeddings (app/ai.py · app/pipeline.py)", font=F(18, "Medium"), fill=MUTED, anchor="mm")
        for i, (lab, col, rule, note) in enumerate(rows):
            e = ease((t - 0.3 - i * 0.3) / 0.6)
            y = 210 + i * 104; x = 120 + int(40 * (1 - e))
            d.rounded_rectangle((x, y, x + 1040, y + 84), 16, fill=mix(NAVY, NAVY2, e), outline=mix(NAVY, col, e), width=2)
            d.rounded_rectangle((x + 18, y + 20, x + 218, y + 64), 12, fill=mix(NAVY, col, e))
            d.text((x + 118, y + 42), lab, font=F(19, "Bold"), fill=mix(NAVY, (255, 255, 255), e), anchor="mm")
            d.text((x + 245, y + 42), rule, font=F(19, "Medium"), fill=mix(NAVY, ON, e), anchor="lm")
            d.text((x + 1020, y + 42), note, font=F(15, "Bold"), fill=mix(NAVY, col, e), anchor="rm")
        emit(fade(img, t / 0.3, (sec - t) / 0.3))

# ---------- demo set (from manifest) ----------
def demo_set(sec=7.0):
    man = json.load(open(ROOT / "demo_assets" / "manifest.json"))
    photos = man["photos"]; review = man.get("review_student")
    appear = [(p, sid) for p, ids in photos.items() for sid in ids]
    uniq = sorted(set(s for _, s in appear))
    def kind(s):
        if s.startswith("S"): return "UNKNOWN"
        n = int(s[-3:])
        if n > 64: return "OTHER CLASS"
        return "REVIEW" if s == review else "PRESENT"
    cols = {"PRESENT": GREEN, "REVIEW": CYAN, "OTHER CLASS": ORANGE, "UNKNOWN": GREY}
    counts = {k: sum(kind(s) == k for s in uniq) for k in cols}
    absent = 64 - sum(1 for s in uniq if not s.startswith("S") and int(s[-3:]) <= 64)
    for k in range(int(sec * FPS)):
        t = k / FPS; img = BG.copy(); d = ImageDraw.Draw(img)
        topbar(d, "THE DEMO SET")
        d.text((W / 2, 112), f"{len(photos)} photos  →  {len(appear)} face appearances  →  {len(uniq)} different people", font=FX(34), fill=ON, anchor="mm")
        d.text((W / 2, 150), "Data Science · Section A (64 students)  —  ground truth from demo_assets/manifest.json", font=F(17, "Medium"), fill=MUTED, anchor="mm")
        # left: photos as columns of chips
        m = ease_io((t - 2.0) / 1.6)   # merge progress
        for pi, (pname, ids) in enumerate(photos.items()):
            ep = ease((t - 0.2 - pi * 0.25) / 0.5)
            x = 80 + pi * 120
            d.rounded_rectangle((x, 190, x + 100, 228), 10, fill=mix(NAVY, NAVY2, ep), outline=mix(NAVY, MUTED, ep))
            d.text((x + 50, 209), f"Photo {pi + 1}", font=F(14, "Bold"), fill=mix(NAVY, ON, ep), anchor="mm")
            for j, s in enumerate(ids):
                ex = x + 12; ey = 240 + j * 33
                # target slot on the right
                ui = uniq.index(s); tx = 640 + (ui % 5) * 116; ty = 220 + (ui // 5) * 66
                cx = ex + (tx - ex) * m; cy = ey + (ty - ey) * m
                c = cols[kind(s)]
                a = ep * (1.0 if m < 0.98 or (pi == [i for i, (_, v) in enumerate(photos.items()) if s in v][0]) else 0)
                if a <= 0: continue
                lab = s[-3:] if not s.startswith("S") else s
                d.rounded_rectangle((cx, cy, cx + 76, cy + 28), 8, fill=mix(NAVY, c, a))
                d.text((cx + 38, cy + 14), lab, font=F(14, "Bold"), fill=mix(NAVY, (255, 255, 255), a), anchor="mm")
        em = ease((t - 3.4) / 0.6)
        d.text((640 + 2.5 * 116 - 20, 194), "after merging duplicates", font=F(15, "Bold"), fill=mix(NAVY, AMBER, em), anchor="mm")
        # totals
        er = ease((t - 4.0) / 0.7)
        x = 140; y = 590
        for lab in ["PRESENT", "REVIEW", "OTHER CLASS", "UNKNOWN"]:
            d.rounded_rectangle((x, y, x + 190, y + 80), 14, fill=mix(NAVY, NAVY2, er), outline=mix(NAVY, cols[lab], er), width=2)
            d.text((x + 95, y + 30), str(int(round(counts[lab] * er))), font=FX(34), fill=mix(NAVY, cols[lab], er), anchor="mm")
            d.text((x + 95, y + 62), lab, font=F(14, "Bold"), fill=mix(NAVY, ON, er), anchor="mm"); x += 205
        d.rounded_rectangle((x, y, x + 190, y + 80), 14, fill=mix(NAVY, NAVY2, er), outline=mix(NAVY, RED, er), width=2)
        d.text((x + 95, y + 30), str(int(round(absent * er))), font=FX(34), fill=mix(NAVY, (255, 120, 130), er), anchor="mm")
        d.text((x + 95, y + 62), "ABSENT", font=F(14, "Bold"), fill=mix(NAVY, ON, er), anchor="mm")
        d.text((W / 2, 700), "Expected outcome of the controlled demo set — one student is deliberately hard so the review step is exercised.", font=F(14, "Medium"), fill=mix(NAVY, MUTED, er), anchor="mm")
        emit(fade(img, t / 0.3, (sec - t) / 0.3))

# ---------- screens ----------
SCREENS = [
    ("01-home.png", "Home", "Demo accounts and the four classroom photos (blurred here)"),
    ("03-admin-dashboard.png", "Admin dashboard", "128 students · teachers · subjects · face profiles"),
    ("04-admin-students.png", "Students", "Synthetic roster: Student 001 – Student 128, two sections"),
    ("05-admin-face-enrollment.png", "Face enrollment", "Enrol 1–5 photos per student or the demo gallery"),
    ("07-admin-subject-groups.png", "Subject groups", "Core and elective rosters decide who is eligible"),
    ("08-admin-timetable.png", "Timetable", "Weekday slots link teacher, subject and group"),
    ("11-teacher-dashboard.png", "Teacher — today", "Today's classes and live totals"),
    ("15-teacher-attendance-photos.png", "Take attendance", "Upload 3–4 photos, then run AI recognition"),
    ("16-teacher-reports.png", "Reports", "Attendance PDF and the separate Other-Class PDF"),
]
def browser(shot, zoom, pan):
    bw, bh = 980, 600; bar = 34
    fr = Image.new("RGBA", (bw, bh), (255, 255, 255, 255)); d = ImageDraw.Draw(fr)
    d.rectangle((0, 0, bw, bar), fill=(236, 233, 226))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((14 + i * 20, 11, 26 + i * 20, 23), fill=c)
    d.rounded_rectangle((90, 6, bw - 90, 28), 11, fill=(255, 255, 255))
    d.text((bw / 2, 17), "127.0.0.1:5000  —  Smart Attendance System", font=F(13, "Medium"), fill=(110, 110, 120), anchor="mm")
    vw, vh = bw, bh - bar; sw, sh = shot.size
    cw = sw / zoom; ch = cw * vh / vw
    cx = (sw - cw) * pan[0]; cy = max(0, min(sh - ch, (sh - ch) * pan[1]))
    fr.paste(shot.crop((int(cx), int(cy), int(cx + cw), int(cy + ch))).resize((vw, vh), Image.LANCZOS), (0, bar))
    mask = Image.new("L", (bw, bh), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), 14, fill=255)
    fr.putalpha(mask); return fr

def screen(i, file, title, sub, sec=3.3):
    shot = Image.open(SHOTS / file).convert("RGB")
    for k in range(int(sec * FPS)):
        t = k / FPS; img = BG.copy()
        z = 1.0 + 0.22 * ease_io((t - 0.9) / 2.2)
        fr = browser(shot, z, (0.5, 0.15 * ease_io((t - 0.9) / 2.2)))
        e = ease(t / 0.5); x, y = 150, 84 + int(30 * (1 - e))
        sh = Image.new("RGBA", (fr.width + 60, fr.height + 60), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((30, 40, fr.width + 30, fr.height + 30), 16, fill=(0, 0, 0, 150))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)), (x - 30, y - 30)); img.alpha_composite(fr, (x, y))
        d = ImageDraw.Draw(img); topbar(d, f"SCREEN {i + 1:02d} / {len(SCREENS)}")
        ec = ease((t - 0.3) / 0.5)
        cw = max(d.textlength(title, font=F(26, "Bold")), d.textlength(sub, font=F(16, "Medium"))) + 50
        cx, cy = 110, 604 + int(20 * (1 - ec))
        d.rounded_rectangle((cx, cy, cx + cw, cy + 86), 16, fill=mix(NAVY, NAVY2, ec), outline=mix(NAVY, ORANGE, ec), width=2)
        d.rectangle((cx + 2, cy + 18, cx + 6, cy + 68), fill=mix(NAVY, ORANGE, ec))
        d.text((cx + 24, cy + 30), title, font=F(26, "Bold"), fill=mix(NAVY, ON, ec), anchor="lm")
        d.text((cx + 24, cy + 62), sub, font=F(16, "Medium"), fill=mix(NAVY, MUTED, ec), anchor="lm")
        emit(fade(img, t / 0.25, (sec - t) / 0.25))

def outro(sec=3.4):
    for k in range(int(sec * FPS)):
        t = k / FPS; img = BG.copy(); d = ImageDraw.Draw(img)
        e = ease(t / 0.7)
        logo(d, W / 2 - 34, 170, 1.55)
        d.text((W / 2, 290), "Smart College Attendance", font=FX(52), fill=mix(NAVY, ON, e), anchor="mm")
        e2 = ease((t - 0.5) / 0.7)
        cmd = "pip install -r requirements.txt  &&  flask --app wsgi run"
        w = d.textlength(cmd, font=F(19, "Medium")) + 50
        d.rounded_rectangle((W / 2 - w / 2, 350, W / 2 + w / 2, 400), 12, fill=mix(NAVY, (10, 18, 34), e2), outline=mix(NAVY, ORANGE, e2))
        d.text((W / 2, 375), cmd, font=F(19, "Medium"), fill=mix(NAVY, (255, 200, 140), e2), anchor="mm")
        d.text((W / 2, 455), "github.com/nvaltryek-001/smart-attendance-demo", font=F(19, "Medium"), fill=mix(NAVY, MUTED, ease((t - 1) / 0.7)), anchor="mm")
        emit(fade(img, t / 0.3, (sec - t) / 0.4))

if __name__ == "__main__":
    intro(); workflow(); rules(); demo_set()
    for i, s in enumerate(SCREENS):
        screen(i, *s)
    outro()
    print("frames", n_frame, "->", OUT)
