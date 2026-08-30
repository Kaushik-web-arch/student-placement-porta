-- Student Placement Portal database
-- Portfolio maintainer: Kaushik Santhosh

CREATE DATABASE IF NOT EXISTS placement_portal;

USE placement_portal;

-- =========================
-- ADMINS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,

    username VARCHAR(50) UNIQUE NOT NULL,

    password VARCHAR(255) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Local demo administrator. Change this password after first login.
-- Username: admin | Password: admin123

INSERT IGNORE INTO admins(username,password)
VALUES(
    'admin',
    'pbkdf2:sha256:600000$kaushik-demo-admin$491de51b64d75c546538a6f96db52253a124385d2fe9304245d2ef91049d0f98'
);

-- =========================
-- STUDENTS TABLE
-- =========================

CREATE TABLE IF NOT EXISTS students (

    id INT AUTO_INCREMENT PRIMARY KEY,

    usn VARCHAR(30) UNIQUE NOT NULL,

    username VARCHAR(50) UNIQUE,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(100),

    branch VARCHAR(50),

    password VARCHAR(255),

    -- Visible to administrators only until the student chooses a private password.
    temporary_password VARCHAR(255),

    first_login BOOLEAN DEFAULT TRUE,

    missed_companies INT DEFAULT 0,

    debarred BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- =========================
-- COMPANIES TABLE
-- =========================

CREATE TABLE IF NOT EXISTS companies (

    id INT AUTO_INCREMENT PRIMARY KEY,

    company_name VARCHAR(100) NOT NULL,

    drive_date DATE,

    package FLOAT,

    description TEXT,

    eligible_branches VARCHAR(255),

    min_cgpa FLOAT DEFAULT 0,

    attendance_marked BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- =========================
-- ATTENDANCE TABLE
-- =========================

CREATE TABLE IF NOT EXISTS attendance (

    id INT AUTO_INCREMENT PRIMARY KEY,

    student_id INT,

    company_id INT,

    status ENUM('Attended','Missed'),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
        REFERENCES students(id)
        ON DELETE CASCADE,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
        ON DELETE CASCADE

);

-- =========================
-- FEEDBACK PARAMETERS
-- =========================

CREATE TABLE IF NOT EXISTS feedback_parameters (

    id INT AUTO_INCREMENT PRIMARY KEY,

    parameter_name VARCHAR(100) UNIQUE

);

INSERT IGNORE INTO feedback_parameters(parameter_name)
VALUES
('Communication'),
('Technical Skills'),
('Problem Solving'),
('DSA'),
('Confidence'),
('Aptitude');

-- =========================
-- COMPANY FEEDBACK
-- =========================

CREATE TABLE IF NOT EXISTS company_feedback (

    id INT AUTO_INCREMENT PRIMARY KEY,

    student_id INT,

    company_id INT,

    communication VARCHAR(20),

    technical_skills VARCHAR(20),

    problem_solving VARCHAR(20),

    dsa VARCHAR(20),

    confidence VARCHAR(20),

    aptitude VARCHAR(20),

    comments TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
        REFERENCES students(id)
        ON DELETE CASCADE,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
        ON DELETE CASCADE

);

-- =========================
-- DAILY QUESTIONS
-- =========================

CREATE TABLE IF NOT EXISTS daily_questions (

    id INT AUTO_INCREMENT PRIMARY KEY,

    question_text TEXT,

    category VARCHAR(50),

    upload_date DATE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

-- =========================
-- QUESTION ATTEMPTS
-- =========================

CREATE TABLE IF NOT EXISTS question_attempts (

    id INT AUTO_INCREMENT PRIMARY KEY,

    student_id INT,

    question_id INT,

    attempted BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
        REFERENCES students(id)
        ON DELETE CASCADE,

    FOREIGN KEY(question_id)
        REFERENCES daily_questions(id)
        ON DELETE CASCADE

);

-- =========================
-- NOTIFICATIONS
-- =========================

CREATE TABLE IF NOT EXISTS notifications (

    id INT AUTO_INCREMENT PRIMARY KEY,

    student_id INT,

    title VARCHAR(255),

    message TEXT,

    is_read BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
        REFERENCES students(id)
        ON DELETE CASCADE

);

-- =========================
-- PLACEMENT RESULTS
-- =========================

CREATE TABLE IF NOT EXISTS placement_results (

    id INT AUTO_INCREMENT PRIMARY KEY,

    student_id INT,

    company_id INT,

    result ENUM('Selected','Rejected','Waitlisted'),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(student_id)
        REFERENCES students(id)
        ON DELETE CASCADE,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
        ON DELETE CASCADE

);
