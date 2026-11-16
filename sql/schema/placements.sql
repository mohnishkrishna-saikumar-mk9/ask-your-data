-- Placements schema: one table of MBA students with scores and placement outcome.
-- Re-runnable: drops and recreates everything.
CREATE SCHEMA IF NOT EXISTS placements;
DROP TABLE IF EXISTS placements.students CASCADE;

CREATE TABLE placements.students (
    student_id                 INTEGER PRIMARY KEY,
    gender                     TEXT NOT NULL CHECK (gender IN ('M', 'F')),
    ssc_percent                NUMERIC(5, 2),
    ssc_board                  TEXT,
    hsc_percent                NUMERIC(5, 2),
    hsc_board                  TEXT,
    hsc_stream                 TEXT,
    degree_percent             NUMERIC(5, 2),
    degree_field               TEXT,
    has_work_experience        BOOLEAN NOT NULL,
    employability_test_percent NUMERIC(5, 2),
    mba_specialisation         TEXT,
    mba_percent                NUMERIC(5, 2),
    is_placed                  BOOLEAN NOT NULL,
    salary                     NUMERIC(12, 2)
);

CREATE INDEX idx_students_spec ON placements.students (mba_specialisation);

COMMENT ON TABLE placements.students IS 'One row per MBA student from one campus with school, degree and MBA scores and placement outcome';
COMMENT ON COLUMN placements.students.student_id IS 'Student serial number (primary key)';
COMMENT ON COLUMN placements.students.gender IS 'M or F';
COMMENT ON COLUMN placements.students.ssc_percent IS 'Class 10 (Secondary School Certificate) percentage';
COMMENT ON COLUMN placements.students.ssc_board IS 'Class 10 board: Central or Others';
COMMENT ON COLUMN placements.students.hsc_percent IS 'Class 12 (Higher Secondary Certificate) percentage';
COMMENT ON COLUMN placements.students.hsc_board IS 'Class 12 board: Central or Others';
COMMENT ON COLUMN placements.students.hsc_stream IS 'Class 12 stream: Commerce, Science or Arts';
COMMENT ON COLUMN placements.students.degree_percent IS 'Undergraduate degree percentage';
COMMENT ON COLUMN placements.students.degree_field IS 'Undergraduate field: Comm&Mgmt, Sci&Tech or Others';
COMMENT ON COLUMN placements.students.has_work_experience IS 'TRUE if the student had work experience before the MBA';
COMMENT ON COLUMN placements.students.employability_test_percent IS 'Employability test score (percentage) conducted by the college';
COMMENT ON COLUMN placements.students.mba_specialisation IS 'MBA specialisation: Mkt&Fin or Mkt&HR';
COMMENT ON COLUMN placements.students.mba_percent IS 'MBA percentage';
COMMENT ON COLUMN placements.students.is_placed IS 'TRUE if the student got a job offer. Placement rate = AVG(is_placed::int)';
COMMENT ON COLUMN placements.students.salary IS 'Annual salary offered in INR; NULL when not placed';
