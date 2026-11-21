<div align="center">

<img src="docs/demo/banner.svg" alt="Smart College Attendance – AI-powered classroom attendance using face recognition" width="100%"/>

# 🎓 Smart College Attendance System: Demo (Stage 1)

**AI-powered classroom attendance using face recognition, with the teacher always in control**

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/InsightFace-ArcFace-e07a00?style=for-the-badge" alt="InsightFace"/>
  <img src="https://img.shields.io/badge/ONNX_Runtime-CPU-005CED?style=for-the-badge&logo=onnx&logoColor=white" alt="ONNX Runtime"/>
  <br/>
  <img src="https://img.shields.io/badge/OpenCV-4.13-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV"/>
  <img src="https://img.shields.io/badge/SQLite-database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/ReportLab-PDF-b00020?style=for-the-badge" alt="ReportLab"/>
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
</p>

<p>
  <img src="https://img.shields.io/badge/Students-128_(synthetic)-50af28?style=flat-square" alt="128 students"/>
  <img src="https://img.shields.io/badge/Face_profiles-18-00aad2?style=flat-square" alt="18 face profiles"/>
  <img src="https://img.shields.io/badge/Photos_per_class-3–4-e07a00?style=flat-square" alt="3-4 photos"/>
  <img src="https://img.shields.io/badge/Mode-DEMO_ONLY-b00020?style=flat-square" alt="Demo only"/>
</p>

**[🎬 Demo](#-demo-video) · [✨ Features](#-key-features) · [🔄 Workflow](#-system-workflow) · [🧠 AI pipeline](#-ai-and-face-recognition-pipeline) · [📸 Screens](#-screenshots) · [⚙️ Install](#%EF%B8%8F-installation-and-setup) · [🎤 Presenting](#-demo-presentation-guide)**

</div>

> [!IMPORTANT]
> **DEMO MODE ONLY.** This project uses synthetic student records (`Student 001`–`Student 128`) and a controlled face dataset.
> It contains no real college attendance data. Don't use it as a production attendance system, and don't mix its database,
> face gallery, credentials or reports with a future real-college deployment.

---

## 🎬 Demo video

<div align="center">

<a href="docs/demo/attendance-tour.mp4">
  <img src="docs/demo/attendance-tour.gif" alt="Product tour: workflow, decision rules, the demo set merging 36 face appearances into 20 people, and nine real application screens" width="100%"/>
</a>

**▶️ [Watch the full-quality MP4 (55 s, 1280×720)](docs/demo/attendance-tour.mp4)**

</div>

| ⏱️ | Scene | What you see |
|:-:|---|---|
| 0:00 | **Intro** | What the system does and who it was built for |
| 0:04 | **Workflow** | Seven steps: upload, detect, recognise, merge, roster check, review, finalize |
| 0:10 | **Decision rules** | The thresholds behind **PRESENT**, **REVIEW**, **OTHER CLASS** and **UNKNOWN** |
| 0:15 | **The demo set** | 4 photos → 36 face appearances → **20 different people**, with duplicates merging live |
| 0:22 | **9 app screens** | Home → admin dashboard → students → face enrollment → subject groups → timetable → teacher view → take attendance → reports |

> [!NOTE]
> The app screens are **real screenshots** of this application running locally, with the demo database seeded.
> **Classroom photos are blurred** in the screenshots and video. The *demo set* scene shows the **expected outcome** from
> `demo_assets/manifest.json` (the ground truth used by the tests); it is not a live recognition run. The video is rendered by
> [`scripts/demo/render_tour_video.py`](scripts/demo/render_tour_video.py).

<p align="center">
  <img src="docs/demo/tour-workflow.jpg" width="32%" alt="Workflow"/>
  <img src="docs/demo/tour-rules.jpg" width="32%" alt="Decision rules"/>
  <img src="docs/demo/tour-demo-set.jpg" width="32%" alt="Demo set"/>
</p>

---

## 🚀 Overview

Marking attendance by calling out 60+ names wastes 5–10 minutes of every lecture. Here, the teacher takes **3–4 photos of the classroom** and the system:

1. 🔍 **detects** every face in every photo,
2. 🧠 **recognises** enrolled students with InsightFace (ArcFace embeddings),
3. 🔗 **merges** the same student seen in several photos into one row,
4. 📋 **checks the subject roster**, so a student from another section is flagged as **OTHER CLASS** instead of being marked present,
5. 👩‍🏫 lets the **teacher review** anything uncertain, and
6. 📄 produces an **Attendance PDF** and a separate **Other-Class PDF**.

> The AI prepares the list. **The teacher makes the final decision.**

## ✨ Key features

<table>
<tr>
<td width="50%" valign="top">

### 🧠 AI and recognition
- 📸 **Multi-photo processing**: 3–4 classroom photos per session
- 🙂 **Face detection + recognition** with InsightFace (`buffalo_sc`)
- 🔗 **Duplicate merging** across photos, for strangers as well
- 📋 **Subject eligibility check** for core and elective rosters
- 🟢🔵🟠⚪ **Four clear outcomes**: Present · Review · Other class · Unknown
- 🛡️ **Never accuses on a weak match**: low similarity becomes *Unknown*

</td>
<td width="50%" valign="top">

### 🏫 College workflow
- 👤 **Two roles**: admin (set-up) and teacher (attendance)
- 🗂️ **Admin**: students, enrollment, face enrollment, subjects, groups, teachers, assignments, timetable
- 📅 **Teacher**: today's classes, start attendance, upload, run AI, review, finalize
- 🖼️ **Face crops** shown for every decision during review
- 📄 **PDF reports** (ReportLab) for attendance and other-class sightings
- 🐳 **Docker** image · optional **Vercel** front door · 📱 mobile-friendly UI

</td>
</tr>
</table>

## 🏫 Demo environment

| Parameter | Demo configuration |
|---|---|
| 🏛️ College | Sai Vidya Institute of Technology |
| 💻 Department | CSE – Data Science |
| 🎓 Semester | 7th Semester |
| 🅰️ Section A | Student 001 – Student 064 (`01DEMO23DS001`–`064`) |
| 🅱️ Section B | Student 065 – Student 128 (`01DEMO23DS065`–`128`) |
| 📘 Core subject | **Data Science** (Section A, 64 students) |
| 📗 Elective | **Cloud Computing** (A+B elective group, 64 students) |
| 🗓️ Timetable | Every weekday: Hour 1 09:00–10:00 (Data Science), Hour 5 13:30–14:30 (Cloud Computing) |
| 🙂 Face profiles | 18 enrolled identities (3 gallery photos each) |

## 🔄 System workflow

```mermaid
flowchart LR
    A["👩‍🏫 Teacher starts<br/>today's class"] --> B["📸 Upload 3–4<br/>classroom photos"]
    B --> C["🔍 Detect faces"]
    C --> D["🧠 ArcFace embedding<br/>vs enrolled gallery"]
    D --> E["🔗 Merge duplicates<br/>across photos"]
    E --> F{"📋 On this subject's<br/>roster?"}
    F -- "yes, confident" --> P["🟢 PRESENT"]
    F -- "yes, uncertain" --> R["🔵 REVIEW"]
    F -- "no, but recognised" --> O["🟠 OTHER CLASS"]
    D -- "no confident match" --> U["⚪ UNKNOWN"]
    P & R --> V["👩‍🏫 Teacher review"]
    V --> Z["✅ Finalize<br/>📄 Attendance PDF"]
    O --> Y["📄 Other-Class PDF"]

    style A fill:#13213c,color:#fff,stroke:#e07a00
    style B fill:#e07a00,color:#fff
    style C fill:#00aad2,color:#fff
    style D fill:#00aad2,color:#fff
    style E fill:#00aad2,color:#fff
    style F fill:#13213c,color:#fff,stroke:#f0b428
    style P fill:#50af28,color:#fff
    style R fill:#00aad2,color:#fff
    style O fill:#e07a00,color:#fff
    style U fill:#969ba5,color:#fff
    style V fill:#f0b428,color:#000
    style Z fill:#50af28,color:#fff
    style Y fill:#b00020,color:#fff
```

## 🧠 AI and face-recognition pipeline

| Stage | What happens | Code |
|---|---|---|
| **Quality and decode** | Each photo is read, checked and resized | `app/ai.py → read_image, image_quality` |
| **Detection** | InsightFace finds every face (bounding box + landmarks) | `ai.detect_boxes` |
| **Embedding** | Each face becomes a 512-d ArcFace vector | `ai.embed_faces` |
| **Matching** | Cosine similarity against every enrolled student's gallery; the best and second-best scores are kept | `ai.match` |
| **Classification** | Thresholds below | `ai.classify` |
| **Merging** | The same student across photos keeps the best detection. Strangers seen twice (similarity ≥ 0.45) count once | `app/pipeline.py` |
| **Roster check** | A confidently recognised student who isn't eligible for the subject becomes **OTHER CLASS** | `app/pipeline.py` |
| **Annotated output** | Colour-coded boxes on each photo, plus face crops for review | `app/pipeline.py` |

## 🎯 Attendance classification rules

| Result | Rule | What happens |
|---|---|---|
| 🟢 **PRESENT** | similarity ≥ **0.50** *and* at least **0.08** ahead of the next-best student | Marked present (the teacher can still change it) |
| 🔵 **REVIEW** | similarity ≥ **0.35** but not confident enough for PRESENT | The teacher confirms or rejects using the face crop |
| 🟠 **OTHER CLASS** | Confidently recognised, but **not on this subject's roster** | Listed in a separate Other-Class PDF; never marked present or absent |
| ⚪ **UNKNOWN** | No confident match, or a weak match to a non-roster student | Not counted; no one is accused |
| 🔴 **ABSENT** | On the roster but not seen in any photo | Listed as absent in the Attendance PDF |

`T_PRESENT` and `T_REVIEW` can be tuned with environment variables.

## 📊 Demo dataset and scale

The four classroom photos are composites built for this demo (`scripts/build_demo_assets.py`). The ground truth in `demo_assets/manifest.json` is used **only by the tests**; the app never reads it.

| | Count |
|---|:-:|
| 📸 Classroom photos | **4** |
| 🙂 Face appearances across all photos | **36** |
| 👥 Different people after merging | **20** |
| 🟢 Section A students expected **PRESENT** | **14** |
| 🔵 Deliberately hard case → **REVIEW** | **1** (Student 003) |
| 🟠 Section B students → **OTHER CLASS** for Data Science | **3** (065, 066, 067) |
| ⚪ Strangers → **UNKNOWN** | **2** |
| 🔴 Section A students not in any photo → **ABSENT** | **49** |

## 🔑 Demo credentials

| Role | Email | Password |
|---|---|---|
| 🛠️ Admin | `admin.demo@college.edu` | `Admin@12345` |
| 👩‍🏫 Teacher | `teacher.demo@college.edu` | `Demo@12345` |

> ⚠️ These are public demo passwords. Change `SECRET_KEY` and both passwords before putting this anywhere reachable.

## 📸 Screenshots

| 🏠 Home | 🛠️ Admin dashboard |
|:-:|:-:|
| <img src="docs/screenshots/01-home.png" alt="Home"/> | <img src="docs/screenshots/03-admin-dashboard.png" alt="Admin dashboard"/> |
| **👥 Students (128)** | **🙂 Face enrollment** |
| <img src="docs/screenshots/04-admin-students.png" alt="Students"/> | <img src="docs/screenshots/05-admin-face-enrollment.png" alt="Face enrollment"/> |
| **📚 Subjects** | **🧩 Subject / elective groups** |
| <img src="docs/screenshots/06-admin-subjects.png" alt="Subjects"/> | <img src="docs/screenshots/07-admin-subject-groups.png" alt="Subject groups"/> |
| **🗓️ Timetable** | **👩‍🏫 Teachers** |
| <img src="docs/screenshots/08-admin-timetable.png" alt="Timetable"/> | <img src="docs/screenshots/09-admin-teachers.png" alt="Teachers"/> |
| **📅 Teacher: today** | **📘 My classes** |
| <img src="docs/screenshots/11-teacher-dashboard.png" alt="Teacher dashboard"/> | <img src="docs/screenshots/12-teacher-classes.png" alt="Classes"/> |
| **📸 Take attendance (photos blurred)** | **📄 Reports** |
| <img src="docs/screenshots/15-teacher-attendance-photos.png" alt="Attendance upload"/> | <img src="docs/screenshots/16-teacher-reports.png" alt="Reports"/> |

| 📱 Mobile: login | 📱 Mobile: teacher dashboard | 🔐 Admin login |
|:-:|:-:|:-:|
| <img src="docs/screenshots/18-mobile-login.png" width="220" alt="Mobile login"/> | <img src="docs/screenshots/19-mobile-dashboard.png" width="220" alt="Mobile dashboard"/> | <img src="docs/screenshots/02-admin-login.png" width="420" alt="Admin login"/> |

## 🧰 Technology stack

| Layer | Tools |
|---|---|
| 🧠 AI / CV | InsightFace (`buffalo_sc`: detector + ArcFace) · ONNX Runtime (CPU) · OpenCV · NumPy · scikit-image |
| ⚡ Backend | Flask 3.1 · Werkzeug · Gunicorn |
| 💾 Storage | SQLite (`app/schema.sql`) · local files for photos, crops and PDFs |
| 📄 Reports | ReportLab |
| 🖥️ Frontend | Server-rendered Jinja templates · custom CSS · mobile-friendly |
| 🧪 Testing | pytest end-to-end acceptance test · Playwright |
| 🚢 Deploy | Docker (one service runs UI + API + AI) · optional Vercel proxy |

## 📁 Project structure

```text
smart-attendance-demo/
├── app/
│   ├── __init__.py        # app factory, routes, demo banner
│   ├── ai.py              # InsightFace engine, detection, embeddings, matching, thresholds
│   ├── pipeline.py        # multi-photo processing, merging, roster check, annotated images
│   ├── enroll.py          # face enrollment (gallery → embeddings)
│   ├── admin.py           # admin pages: students, faces, subjects, groups, teachers, timetable
│   ├── teacher.py         # teacher pages: today, classes, attendance, review, reports
│   ├── reports.py         # Attendance PDF + Other-Class PDF
│   ├── auth.py · db.py · seed.py · schema.sql
│   ├── templates/         # admin/ and teacher/ Jinja templates
│   └── static/style.css
├── demo_assets/           # demo face gallery, 4 classroom photos, manifest.json (see the note below)
├── docs/
│   ├── demo/              # tour video (MP4 + GIF), banner, stills
│   └── screenshots/       # real app screenshots (photos blurred)
├── scripts/
│   ├── build_demo_assets.py   # builds the controlled demo face set
│   ├── seed_demo.py           # (re)seeds the demo database
│   └── demo/render_tour_video.py
├── tests/test_e2e.py      # end-to-end acceptance test (real pipeline + PDFs)
├── Dockerfile · vercel.json · DEPLOY.md · wsgi.py
└── requirements.txt · requirements-dev.txt · .env.example
```

## ⚙️ Installation and setup

```bash
git clone https://github.com/nvaltryek-001/smart-attendance-demo.git
cd smart-attendance-demo

python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then set a long random SECRET_KEY
```

On the first run InsightFace downloads its `buffalo_sc` model pack to `~/.insightface`.

## ▶️ Running the application

```bash
python wsgi.py                      # http://127.0.0.1:5000
# production-style
gunicorn -w 1 --threads 8 -t 300 wsgi:app
```

On first start the demo database is seeded automatically (`AUTO_SEED=1`) with 128 students, subjects, groups, timetable and the 18 face profiles. To reset it:

```bash
python scripts/seed_demo.py
```

**Docker**

```bash
docker build -t smart-attendance-demo .
docker run -p 8000:8000 -v sa_data:/data -e SECRET_KEY=$(openssl rand -hex 32) smart-attendance-demo
```

See [`DEPLOY.md`](DEPLOY.md) for hosting notes and the optional Vercel front door.

## 🎤 Demo presentation guide

1. 🏠 Open the **home page** and save the four classroom photos to your phone.
2. 🛠️ Sign in as **admin**: show the 128 students, subjects, groups, teacher assignments and timetable.
3. 🚪 Log out and sign in as the **teacher**: *Today* shows only this teacher's classes.
4. ▶️ **Start attendance** for *Data Science*.
5. 📸 **Upload the 4 photos** and press **Run AI processing**. Watch the progress steps.
6. 🔍 On **Review**, the expected result is 14 present, Student 003 for review, 3 *other class* and 2 unknown.
7. ✅ Confirm Student 003, then **Finalize**.
8. 📄 Download the **Attendance PDF** and the **Other-Class PDF**. They open on a phone too.
9. 🔄 Reload to show that the data persists.

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest -s tests/test_e2e.py
```

The end-to-end test drives the **real Flask routes, the real InsightFace pipeline and the real PDF generator** through the full demo checklist. It uses `manifest.json` only at the end, to validate the results.

## 📄 Reports

| Report | Contents |
|---|---|
| 📄 **Attendance PDF** | Session details (subject, group, date, hour, faculty) and every rostered student with their final status |
| 📄 **Other-Class PDF** | Recognised students who aren't on this subject's roster, with face crops, kept separate so no one is wrongly marked |

## ⚠️ Known limitations

- **Controlled demo data**: 18 enrolled identities and composite classroom images, so real-classroom accuracy is **not measured**.
- Lighting, distance, occlusion (masks, hands), head angle and crowd size all affect recognition.
- Thresholds (`0.50` / `0.35` / margin `0.08`) were chosen for this demo set and need calibration on real data.
- SQLite and local files need a **persistent disk**. Free hosts that sleep lose uploads and PDFs.
- Nothing has been deployed or tested online yet (see `DEPLOY.md`).

## 🏛️ Moving to the real college version

- 🆕 Use a **fresh database, gallery, secret key and credentials**. Never reuse the demo ones.
- ✍️ Get **written consent** from every student before enrolling a face, and publish a retention policy.
- 📸 Enrol 3–5 photos per student under classroom-like conditions.
- 📏 Re-tune thresholds on a labelled pilot, and measure precision and recall per class.
- 🔐 Add HTTPS, strong passwords or SSO, encrypted storage, backups and audit logging.

## 🔮 Future enhancements

- [ ] Live camera capture and a mobile app
- [ ] Per-student attendance percentage and shortage alerts
- [ ] Bulk enrollment via CSV and photo ZIP
- [ ] SMS or email notifications to parents
- [ ] Integration with the college ERP or LMS
- [ ] Anti-spoofing (liveness) checks

## 📜 Dataset source, license and responsible use

Demo faces come from **LFW (Labeled Faces in the Wild)**, via [deepfunneled_lfw](https://github.com/redwankarimsony/deepfunneled_lfw), and are used for research and demonstration only. LFW images are of real people. Don't use them to identify anyone, and respect the dataset's terms.

Face data is **biometric data**. Any real deployment needs informed consent, a lawful basis under the applicable data-protection law (for example India's DPDP Act 2023), minimal retention and human review of every decision.

<div align="center">

---

**Built with 🎓 + 🤖 to give teachers their lecture time back**

⭐ If you found this project useful, please give it a star!

</div>
