# Smart College Attendance System — DEMO (Stage 1)

> **DEMO MODE.** Synthetic students ("Student 001"…"Student 128") and a controlled face set. Not real college data.
> Do **not** mix this demo with the future production system (see "Moving to the real college version").

Face-recognition attendance for a classroom: teacher uploads 3–4 classroom photos → InsightFace detects and
recognises faces → duplicates across photos are merged → subject eligibility is checked → teacher reviews →
finalizes → Attendance PDF + separate Other-Class PDF.

## Demo data
College: Sai Vidya Institute of Technology · CSE – Data Science · 7th Sem · Sections A (001–064) and B (065–128).
Subjects: **Data Science** (Section A, Hour 1, 09:00–10:00) and **Cloud Computing** (elective, A+B, Hour 5, 14:00–15:00).
Timetable rows exist for every weekday so "Today's classes" is never empty.

| Role | Email | Password |
|---|---|---|
| Admin | admin.demo@college.edu | Admin@12345 |
| Teacher | teacher.demo@college.edu | Demo@12345 |

These are public, documented **demo** credentials. Change `SECRET_KEY` and remove them for any real use.

## AI pipeline (all real, nothing scripted)
* Detector **SCRFD** + recogniser **ArcFace** (InsightFace `buffalo_l`, `w600k_r50`) on **ONNX Runtime (CPU)**, OpenCV for I/O.
* Gallery = embeddings of enrolment photos (`face_embeddings` table). Match = cosine similarity vs. every gallery embedding.
* `PRESENT` sim ≥ 0.50 and top1−top2 ≥ 0.08 · `REVIEW` sim ≥ 0.35 · otherwise `UNKNOWN` (`app/ai.py`).
* Unknown faces seen in several photos are merged (sim ≥ 0.45). Known people seen in several photos are one row.
* Recognised but not on the subject's roster → `OTHER CLASS`. Neither UNKNOWN nor OTHER CLASS is ever absent.
* **Absent = eligible roster − teacher-confirmed present.** Finalized sessions are immutable.
* `demo_assets/manifest.json` is written by the asset builder **for validation only** (tests). The app never reads it.

**Scale honesty:** only 18 identities have face profiles (15 in Section A, 3 in Section B). The database holds 128 students,
but this demo makes **no claim of 128-person accuracy**. With only 15 of 64 Section A students enrolled, most of the roster is
legitimately "Absent" in the demo.

## Dataset source and licensing (read this)
Face identities come from **LFW – Labeled Faces in the Wild** (Huang et al., UMass Amherst), public-figure photos collected
from the web. LFW is intended for **research on unconstrained face recognition**; the underlying photographs remain
the property of their original copyright holders. Therefore:
* LFW, the generated gallery, classroom images, manifest, DB, and PDFs are **private/local and git-ignored**. Do not publish them.
* The four `classroom_0X.jpg` files are **synthetic composites** of LFW photos (different photographs from the gallery ones,
  same identities). They are not real classroom photographs and are for private demonstration only.
* InsightFace's pretrained models are for **non-commercial research use**; a commercial/production college deployment
  needs a model with an appropriate licence (see below).

## Quick start (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # + requirements-dev.txt for tests
cp .env.example .env
# 1) build the private demo assets from a LOCAL LFW copy (layout: <dir>/<Person_Name>/<Person_Name>_0001.jpg)
LFW_DIR=/path/to/lfw python scripts/build_demo_assets.py     # deterministic; ~3 min first run, seconds after (cached)
# 2) run
python wsgi.py                              # http://localhost:5000   (first start seeds DB + enrols faces)
# 3) test
pytest -s tests/test_e2e.py                 # full local acceptance flow (needs demo_assets + poppler-utils)
```
First run downloads the `buffalo_l` model pack (~330 MB on disk; the app loads only the SCRFD detector `det_10g` and ArcFace `w600k_r50`) into `~/.insightface`.

## Demo images (upload these during the presentation)
`demo_assets/classroom/classroom_01.jpg … classroom_04.jpg` — also downloadable from the app's home page.
Upload the **original files** — heavy re-compression (e.g. sending through a chat app) turns the REVIEW case into UNKNOWN.

| Image | Students | Shows |
|---|---|---|
| classroom_01 | 001–008, 065, 1 stranger | Student 003 → 🟡 REVIEW (small, dim back-row face); 065 → 🟠 OTHER CLASS; stranger → ⚪ UNKNOWN |
| classroom_02 | 005–012, 066 | overlap with photo 1 (005–008) → deduplication; 066 → 🟠 |
| classroom_03 | 009–015, 067 | overlap with photo 2 (009–012); 067 → 🟠 |
| classroom_04 | 013–015, 001, 002, 004, 005, 065, 1 stranger | overlaps with all; 065 seen twice → one row; 2nd stranger → ⚪ |

## Layout
```
app/            Flask app (admin.py, teacher.py, auth.py, ai.py, pipeline.py, reports.py, seed.py, db.py, schema.sql, templates/, static/)
scripts/        build_demo_assets.py (LFW → gallery + classroom images), seed_demo.py
tests/          test_e2e.py (acceptance)
wsgi.py         entry point (gunicorn wsgi:app)
Dockerfile, vercel.json, DEPLOY.md
```
The schema is plain relational SQL and maps cleanly to PostgreSQL, but a few statements are SQLite-specific and must be ported later: `INSERT OR IGNORE` (→ `ON CONFLICT DO NOTHING`, in `app/admin.py`) and the `PRAGMA` calls in `app/db.py`.

## Moving to the real college version (do NOT reuse the demo in place)
* New repo/branch/database; import authorized student + faculty data via an audited importer; consent and retention policy first.
* Replace LFW/InsightFace-pretrained with a model whose licence permits your use; evaluate on your own cameras and classrooms.
* Real auth (SSO/hashed per-user passwords, MFA for admin), CSRF protection, rate limiting, HTTPS, secrets manager.
* PostgreSQL + object storage for photos/PDFs; encrypt face embeddings; role-based audit; deletion workflow.
* Calibrate thresholds on real data; measure false-accept/false-reject; keep the teacher-review gate.

## Known limitations
* No CSRF tokens, default demo `SECRET_KEY`, public demo passwords. Demo only.
* Face crops are LFW headshots; real classroom performance (small faces, angles, occlusion) is **not** demonstrated by this data.
* Single worker/process model; SQLite on local disk (use a persistent volume).
