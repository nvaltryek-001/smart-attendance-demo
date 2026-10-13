# 🎓 Smart College Attendance System — DEMO (Stage 1)

**AI-Powered Classroom Attendance Using Face Recognition**

A demonstration project that uses computer vision and face recognition to identify students from classroom photographs, merge duplicate detections, verify subject eligibility, and generate attendance reports for teacher review.

> [!IMPORTANT]
> **DEMO MODE ONLY.** This project uses synthetic student records (`Student 001`–`Student 128`) and a controlled face dataset. It does not contain real college attendance data.
>
> Do not use this demo as a production attendance system or mix its database, face gallery, credentials, or generated reports with a future real-college deployment.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Demo Environment](#-demo-environment)
- [System Workflow](#-system-workflow)
- [AI and Face Recognition Pipeline](#-ai-and-face-recognition-pipeline)
- [Attendance Classification Rules](#-attendance-classification-rules)
- [Demo Dataset and Scale](#-demo-dataset-and-scale)
- [Demo Credentials](#-demo-credentials)
- [Dataset Source and Licensing](#-dataset-source-and-licensing)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Installation and Setup](#-installation-and-setup)
- [Running the Application](#-running-the-application)
- [Demo Presentation Guide](#-demo-presentation-guide)
- [Testing](#-testing)
- [Reports](#-reports)
- [Known Limitations](#-known-limitations)
- [Moving to the Real College Version](#-moving-to-the-real-college-version)
- [Future Enhancements](#-future-enhancements)
- [License and Responsible Use](#-license-and-responsible-use)

## 🚀 Overview

The Smart College Attendance System is a computer-vision-based demonstration designed to automate classroom attendance using multiple photographs.

Instead of requiring the teacher to mark each student manually, the system analyses uploaded classroom images, identifies known faces, merges repeated detections, checks whether recognised students belong to the selected subject, and prepares an attendance report for teacher verification.

The teacher retains control over the final attendance decision.

### The system supports

- Classroom photograph uploads.
- Face detection and face recognition.
- Duplicate detection merging across multiple photographs.
- Subject-wise student eligibility checking.
- Review of uncertain and unidentified faces.
- Identification of recognised students belonging to other classes.
- Teacher-confirmed attendance finalization.
- Attendance PDF and separate Other-Class PDF generation.

**Important:** The system demonstrates a complete workflow with a limited, controlled dataset. It does not establish real-world classroom accuracy or production readiness.

## ✨ Key Features

### 1. Face Recognition Attendance

Uses InsightFace to detect and recognise enrolled identities in classroom photographs.

### 2. Multiple Photograph Processing

Teachers can upload approximately 3–4 classroom images. The pipeline processes the images and combines detections across photographs.

### 3. Duplicate Detection Removal

When the same student appears in multiple photographs, repeated detections are merged so the student can be represented by one attendance row.

### 4. Subject Eligibility Verification

The system checks recognised identities against the roster for the selected subject.

A recognised student who is not eligible for the selected subject is classified as **OTHER CLASS**, rather than being marked absent or counted as present.

### 5. Teacher Review

Uncertain recognition results can be reviewed before attendance is finalized.

### 6. Attendance Reports

The system generates:

- **Attendance PDF:** the finalized attendance report.
- **Other-Class PDF:** a separate report for recognised students who are not on the selected subject's roster.

### 7. Demo Administration and Timetable

The demo includes administrator and teacher roles, synthetic student records, and timetable entries for weekdays.

## 🏫 Demo Environment

The demonstration is configured with the following synthetic academic data.

| Parameter | Demo configuration |
|---|---|
| College | Sai Vidya Institute of Technology |
| Department | CSE – Data Science |
| Semester | 7th Semester |
| Section A | Student 001–Student 064 |
| Section B | Student 065–Student 
