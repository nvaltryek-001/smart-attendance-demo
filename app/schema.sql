-- Portable SQL (SQLite demo; maps 1:1 to PostgreSQL: INTEGER PK -> SERIAL/IDENTITY, BLOB -> BYTEA)
CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS semesters   (id INTEGER PRIMARY KEY, number INTEGER UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS sections    (id INTEGER PRIMARY KEY, name TEXT NOT NULL, department_id INTEGER NOT NULL REFERENCES departments(id),
                                        semester_id INTEGER NOT NULL REFERENCES semesters(id), UNIQUE(name, department_id, semester_id));
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
                                  role TEXT NOT NULL CHECK(role IN ('admin','teacher')), full_name TEXT NOT NULL, is_demo INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                                     department_id INTEGER REFERENCES departments(id), designation TEXT, phone TEXT);
CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, usn TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                                     department_id INTEGER NOT NULL REFERENCES departments(id), semester_id INTEGER NOT NULL REFERENCES semesters(id),
                                     section_id INTEGER NOT NULL REFERENCES sections(id), is_demo INTEGER DEFAULT 1, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                                     department_id INTEGER NOT NULL REFERENCES departments(id), semester_id INTEGER NOT NULL REFERENCES semesters(id),
                                     kind TEXT NOT NULL DEFAULT 'core');
CREATE TABLE IF NOT EXISTS subject_groups (id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id),
                                           name TEXT NOT NULL, label TEXT NOT NULL);   -- label e.g. 'Section A' / 'A+B'
CREATE TABLE IF NOT EXISTS subject_group_students (group_id INTEGER NOT NULL REFERENCES subject_groups(id),
                                                   student_id INTEGER NOT NULL REFERENCES students(id), PRIMARY KEY(group_id, student_id));
CREATE TABLE IF NOT EXISTS teacher_assignments (id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL REFERENCES teachers(id),
                                                subject_id INTEGER NOT NULL REFERENCES subjects(id), group_id INTEGER NOT NULL REFERENCES subject_groups(id),
                                                UNIQUE(teacher_id, group_id));
CREATE TABLE IF NOT EXISTS timetable (id INTEGER PRIMARY KEY, assignment_id INTEGER NOT NULL REFERENCES teacher_assignments(id),
                                      weekday INTEGER NOT NULL, hour_no INTEGER NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS face_profiles (id INTEGER PRIMARY KEY, student_id INTEGER UNIQUE NOT NULL REFERENCES students(id),
                                          status TEXT NOT NULL DEFAULT 'enrolled', enrolled_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS face_embeddings (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES face_profiles(id) ON DELETE CASCADE,
                                            embedding BLOB NOT NULL, det_score REAL, source TEXT);
CREATE TABLE IF NOT EXISTS attendance_sessions (id INTEGER PRIMARY KEY, assignment_id INTEGER NOT NULL REFERENCES teacher_assignments(id),
                                                teacher_id INTEGER NOT NULL REFERENCES teachers(id), subject_id INTEGER NOT NULL, group_id INTEGER NOT NULL,
                                                session_date TEXT NOT NULL, hour_no INTEGER, start_time TEXT, end_time TEXT,
                                                status TEXT NOT NULL DEFAULT 'open',   -- open|processing|review|finalized|failed
                                                stage INTEGER DEFAULT 0, stage_msg TEXT, error TEXT, created_at TEXT NOT NULL, finalized_at TEXT);
CREATE TABLE IF NOT EXISTS attendance_photos (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
                                              filename TEXT NOT NULL, path TEXT NOT NULL, width INTEGER, height INTEGER, blur REAL,
                                              quality_ok INTEGER, faces_detected INTEGER DEFAULT 0, annotated_path TEXT);
CREATE TABLE IF NOT EXISTS attendance_records (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
                                               student_id INTEGER REFERENCES students(id),      -- NULL for unknown faces
                                               ai_result TEXT NOT NULL,     -- PRESENT|REVIEW|OTHER_CLASS|UNKNOWN|NOT_DETECTED
                                               confidence REAL, similarity REAL, photo_id INTEGER, bbox TEXT, crop_path TEXT, seen_in_photos INTEGER DEFAULT 1,
                                               teacher_decision TEXT,       -- PRESENT|ABSENT|NULL
                                               final_status TEXT,           -- PRESENT|ABSENT|OTHER_CLASS|UNKNOWN (set at finalize)
                                               note TEXT);
CREATE TABLE IF NOT EXISTS other_class_detections (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
                                                   record_id INTEGER REFERENCES attendance_records(id), student_id INTEGER NOT NULL REFERENCES students(id),
                                                   confidence REAL, photo_id INTEGER, detected_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attendance_reports (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES attendance_sessions(id),
                                               kind TEXT NOT NULL, path TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, at TEXT NOT NULL, user_id INTEGER, action TEXT NOT NULL, detail TEXT);
CREATE INDEX IF NOT EXISTS idx_students_section ON students(section_id);
CREATE INDEX IF NOT EXISTS idx_records_session ON attendance_records(session_id);
CREATE INDEX IF NOT EXISTS idx_sgs_student ON subject_group_students(student_id);
