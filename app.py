"""Student Placement Portal.

Portfolio maintainer: Kaushik Santhosh
"""

from flask import Flask, render_template, request, redirect, session, flash
import pymysql
import pandas as pd
import random
import string
import os
import secrets
from datetime import date
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
COMPANY_LOGO_FOLDER = "uploads/company_logos"
JD_FOLDER = "uploads/job_descriptions"

app.config["COMPANY_LOGO_FOLDER"] = COMPANY_LOGO_FOLDER
app.config["JD_FOLDER"] = JD_FOLDER

for folder in (UPLOAD_FOLDER, COMPANY_LOGO_FOLDER, JD_FOLDER):
    os.makedirs(folder, exist_ok=True)

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "placement_portal")
    )


def ensure_student_admin_columns(conn):
    """Add the temporary-password column to an existing local database once."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s
          AND TABLE_NAME='students'
          AND COLUMN_NAME='temporary_password'
    """, (os.getenv("DB_NAME", "placement_portal"),))

    if cur.fetchone()[0] == 0:
        cur.execute("""
            ALTER TABLE students
            ADD COLUMN temporary_password VARCHAR(255) NULL
            AFTER password
        """)
        conn.commit()


def admin_csrf_token():
    """Return the per-session token used by admin POST actions."""
    if "admin_csrf_token" not in session:
        session["admin_csrf_token"] = secrets.token_urlsafe(32)
    return session["admin_csrf_token"]


def valid_admin_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("admin_csrf_token", "")
    return bool(submitted and expected) and secrets.compare_digest(submitted, expected)


def end_deleted_student_session():
    """End an old browser session after its student account is deleted."""
    session.pop("student", None)
    session.pop("student_id", None)
    flash("This student account is no longer available.", "warning")
    return redirect("/student_login")


def get_session_student(cur):
    """Load the current student by stable ID so profile edits stay synchronized."""
    student_id = session.get("student_id")

    if student_id:
        cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
    else:
        cur.execute("SELECT * FROM students WHERE usn=%s", (session.get("student"),))

    student = cur.fetchone()
    if student:
        session["student_id"] = student["id"]
        session["student"] = student["usn"]
    return student


def refresh_student_attendance_totals(cur):
    """Keep missed-drive counts and eligibility aligned with attendance rows."""
    cur.execute("""
        UPDATE students AS s
        LEFT JOIN (
            SELECT student_id, COUNT(*) AS missed
            FROM attendance
            WHERE status='Missed'
            GROUP BY student_id
        ) AS totals ON totals.student_id=s.id
        SET s.missed_companies=COALESCE(totals.missed, 0),
            s.debarred=CASE WHEN COALESCE(totals.missed, 0) >= 5 THEN 1 ELSE 0 END
    """)


def password_matches(stored_password, entered_password):
    """Support secure hashes while allowing a one-time legacy DB migration."""
    if not stored_password:
        return False
    if stored_password.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored_password, entered_password)
    return secrets.compare_digest(stored_password, entered_password)


def generate_password():
    return ''.join(
        random.choices(
            string.ascii_letters + string.digits,
            k=8
        )
    )


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute(
            "SELECT * FROM admins WHERE username=%s",
            (username,)
        )

        admin = cur.fetchone()

        conn.close()

        if admin and password_matches(admin["password"], password):
            session["admin"] = username
            return redirect("/dashboard")

        flash("Invalid Credentials", "danger")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM students")
    students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM companies")
    companies = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM students WHERE debarred=1"
    )
    debarred = cur.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        students=students,
        companies=companies,
        debarred=debarred
    )


@app.route("/students")
def students():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    ensure_student_admin_columns(conn)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Student List
    cur.execute("""
        SELECT *
        FROM students
        ORDER BY usn
    """)

    students = cur.fetchall()

    # Build tracker for every student
    for student in students:

        cur.execute("""
            SELECT status
            FROM attendance
            WHERE student_id=%s
            ORDER BY company_id DESC
            LIMIT 5
        """, (student["id"],))

        attendance = cur.fetchall()

        attendance = list(attendance)

        attendance.reverse()

        tracker = []

        for row in attendance:
            tracker.append(row["status"])

        student["tracker"] = tracker

        student["tracker"] = tracker

    # Total Students
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM students
    """)
    total_students = cur.fetchone()["total"]

    # Active Students
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM students
        WHERE debarred=0
    """)
    active_students = cur.fetchone()["total"]

    # Debarred Students
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM students
        WHERE debarred=1
    """)
    debarred_students = cur.fetchone()["total"]

    # Latest Placement Drive
    cur.execute("""
        SELECT company_name
        FROM companies
        ORDER BY drive_date DESC
        LIMIT 1
    """)
    drive = cur.fetchone()

    conn.close()

    return render_template(
        "students.html",
        students=students,
        total_students=total_students,
        active_students=active_students,
        debarred_students=debarred_students,
        drive=drive,
        csrf_token=admin_csrf_token()
    )


@app.route("/reset_student_password/<int:student_id>", methods=["POST"])
def reset_student_password(student_id):
    if "admin" not in session:
        return redirect("/login")

    if not valid_admin_csrf():
        flash("The request expired. Please try again.", "danger")
        return redirect("/students")

    conn = get_db_connection()
    ensure_student_admin_columns(conn)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT id, name FROM students WHERE id=%s", (student_id,))
    student = cur.fetchone()

    if not student:
        conn.close()
        flash("Student not found.", "warning")
        return redirect("/students")

    temporary_password = generate_password()
    cur.execute("""
        UPDATE students
        SET password=%s,
            temporary_password=%s,
            first_login=1
        WHERE id=%s
    """, (
        generate_password_hash(temporary_password),
        temporary_password,
        student_id,
    ))
    conn.commit()
    conn.close()

    flash(f"Temporary password reset for {student['name']}.", "success")
    return redirect("/students")


@app.route("/delete_student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if "admin" not in session:
        return redirect("/login")

    if not valid_admin_csrf():
        flash("The request expired. Please try again.", "danger")
        return redirect("/students")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT id, name, usn FROM students WHERE id=%s", (student_id,))
    student = cur.fetchone()

    if not student:
        conn.close()
        flash("Student not found.", "warning")
        return redirect("/students")

    cur.execute("DELETE FROM students WHERE id=%s", (student_id,))
    conn.commit()
    conn.close()

    flash(f"{student['name']} ({student['usn']}) was deleted.", "success")
    return redirect("/students")

@app.route("/student/<int:id>")
def admin_student_profile(id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT *
        FROM students
        WHERE id=%s
    """,(id,))

    student=cur.fetchone()

    cur.execute("""
        SELECT
            companies.company_name,
            companies.drive_date,
            attendance.status
        FROM attendance

        JOIN companies
        ON attendance.company_id=companies.id

        WHERE attendance.student_id=%s

        ORDER BY companies.drive_date DESC
    """,(id,))

    history=cur.fetchall()

    conn.close()

    return render_template(
        "admin_student_profile.html",
        student=student,
        history=history
    )


@app.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
    student = cur.fetchone()

    if not student:
        conn.close()
        flash("Student not found.", "warning")
        return redirect("/students")

    if request.method == "POST":
        if not valid_admin_csrf():
            conn.close()
            flash("The request expired. Please try again.", "danger")
            return redirect(f"/edit_student/{student_id}")

        usn = request.form.get("usn", "").strip().upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        branch = request.form.get("branch", "").strip().upper()
        debarred = 1 if request.form.get("status") == "debarred" else 0

        if not all((usn, name, email, branch)):
            conn.close()
            flash("USN, name, email and branch are required.", "warning")
            return redirect(f"/edit_student/{student_id}")

        try:
            cur.execute("""
                UPDATE students
                SET usn=%s,
                    username=%s,
                    name=%s,
                    email=%s,
                    branch=%s,
                    debarred=%s
                WHERE id=%s
            """, (usn, usn, name, email, branch, debarred, student_id))
            conn.commit()
        except pymysql.err.IntegrityError:
            conn.rollback()
            conn.close()
            flash("That USN is already assigned to another student.", "danger")
            return redirect(f"/edit_student/{student_id}")

        conn.close()
        flash("Student details updated successfully.", "success")
        return redirect(f"/student/{student_id}")

    conn.close()
    return render_template(
        "edit_student.html",
        student=student,
        csrf_token=admin_csrf_token(),
    )

@app.route("/upload_students", methods=["GET", "POST"])
def upload_students():

    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":

        file = request.files.get("file")

        if not file or not file.filename:
            flash("Choose an Excel file to upload.", "warning")
            return redirect("/upload_students")

        extension = os.path.splitext(file.filename)[1].lower()
        if extension not in {".xlsx", ".xls", ".csv"}:
            flash("Only .xlsx, .xls, or .csv files are supported.", "danger")
            return redirect("/upload_students")

        safe_name = secure_filename(file.filename)

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            safe_name
        )

        file.save(filepath)

        df = pd.read_csv(filepath) if extension == ".csv" else pd.read_excel(filepath)

        required_columns = {"USN", "Name", "Email", "Branch"}
        missing_columns = required_columns.difference(df.columns)
        if missing_columns:
            flash(
                "Missing columns: " + ", ".join(sorted(missing_columns)),
                "danger",
            )
            return redirect("/upload_students")

        conn = get_db_connection()
        ensure_student_admin_columns(conn)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        credentials = []

        for _, row in df.iterrows():

            username = row["USN"]

            temporary_password = generate_password()

            try:

                cur.execute("""
                    INSERT INTO students
                    (
                        usn,
                        username,
                        name,
                        email,
                        branch,
                        password,
                        temporary_password
                    )
                    VALUES(%s,%s,%s,%s,%s,%s,%s)
                """, (
                    row["USN"],
                    username,
                    row["Name"],
                    row["Email"],
                    row["Branch"],
                    generate_password_hash(temporary_password),
                    temporary_password
                ))

                credentials.append({
                    "usn": row["USN"],
                    "name": row["Name"],
                    "temporary_password": temporary_password,
                })

            except Exception as e:
                print("UPLOAD ERROR:", e)

        conn.commit()
        conn.close()

        return render_template(
            "upload_result.html",
            credentials=credentials,
        )

    return render_template(
        "upload_students.html"
    )

@app.route("/student_login", methods=["GET", "POST"])
def student_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        ensure_student_admin_columns(conn)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("""
            SELECT id, usn, username, password, first_login
            FROM students
            WHERE username=%s
        """, (username,))

        student = cur.fetchone()

        conn.close()

        if student:
            db_password = student["password"]

            if password_matches(db_password, password):

                session["student_id"] = student["id"]
                session["student"] = student["usn"]

                if student["first_login"] == 1:
                    return redirect("/change_password")

                return redirect("/student_dashboard")

        flash("Invalid Credentials", "danger")

    return render_template("student_login.html")

@app.route("/student_logout")
def student_logout():

    # Remove student session only
    session.pop("student", None)
    session.pop("student_id", None)

    flash("Logged out successfully!", "success")

    return redirect("/")

@app.route("/change_password", methods=["GET", "POST"])
def change_password():

    if "student" not in session and "student_id" not in session:
        return redirect("/student_login")

    if request.method == "POST":

        new_password = request.form["new_password"]

        conn = get_db_connection()
        ensure_student_admin_columns(conn)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        student = get_session_student(cur)

        if not student:
            conn.close()
            return end_deleted_student_session()

        cur.execute("""
            UPDATE students
            SET password=%s,
                first_login=0,
                temporary_password=NULL
            WHERE id=%s
        """, (
            generate_password_hash(new_password),
            student["id"]
        ))

        conn.commit()
        conn.close()

        return redirect("/student_dashboard")

    return render_template(
        "change_password.html"
    )

@app.route("/student_dashboard")
def student_dashboard():

    if "student" not in session and "student_id" not in session:
        return redirect("/student_login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    student = get_session_student(cur)

    if not student:
        conn.close()
        return end_deleted_student_session()

    progress = student["missed_companies"] * 20

    # Attendance History
    cur.execute("""
        SELECT
            companies.company_name,
            companies.drive_date,
            attendance.status
        FROM attendance

        INNER JOIN companies
        ON attendance.company_id = companies.id

        WHERE attendance.student_id=%s

        ORDER BY companies.drive_date DESC
    """, (student["id"],))

    history = cur.fetchall()

    # ==========================
    # Latest 5 Attendance Tracker
    # ==========================

    cur.execute("""
        SELECT status
        FROM attendance
        WHERE student_id=%s
        ORDER BY company_id DESC
        LIMIT 5
    """, (student["id"],))

    attendance = cur.fetchall()

    tracker = []

    for row in attendance:
        tracker.append(row["status"])

    tracker.reverse()

    conn.close()

    return render_template(
        "student_dashboard.html",
        student=student,
        history=history,
        tracker=tracker,
        progress=progress
    )

@app.route("/student_companies")
def student_companies():

    if "student" not in session and "student_id" not in session:
        return redirect("/student_login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    student = get_session_student(cur)

    if not student:
        conn.close()
        return end_deleted_student_session()

    # Get all companies with student's attendance
    cur.execute("""
        SELECT
            companies.id,
            companies.company_name,
            companies.drive_date,
            
            attendance.status AS attendance_status

        FROM companies

        LEFT JOIN attendance
        ON companies.id = attendance.company_id
        AND attendance.student_id = %s

        ORDER BY companies.drive_date DESC
    """, (student["id"],))

    companies = cur.fetchall()

    conn.close()

    return render_template(
        "student_companies.html",
        companies=companies,
        student=student,
        today=date.today()
    )

@app.route("/student_profile")
def student_profile():

    if "student" not in session and "student_id" not in session:
        return redirect("/student_login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    student = get_session_student(cur)

    if not student:
        conn.close()
        return end_deleted_student_session()

    # Placement History
    cur.execute("""
        SELECT
            companies.company_name,
            companies.drive_date,
            attendance.status
        FROM attendance

        INNER JOIN companies
        ON attendance.company_id = companies.id

        WHERE attendance.student_id=%s

        ORDER BY companies.drive_date DESC
    """, (student["id"],))

    history = cur.fetchall()

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        history=history
    )

@app.route("/add_company", methods=["GET", "POST"])
def add_company():

    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":

        company_name = request.form["company_name"]
        drive_date = request.form["drive_date"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO companies
            (
                company_name,
                drive_date
            )
            VALUES
            (%s,%s)
        """,
        (
            company_name,
            drive_date
        ))

        conn.commit()
        conn.close()

        flash("Company Added Successfully", "success")

        return redirect("/companies")

    return render_template("add_company.html")

@app.route("/edit_company/<int:id>", methods=["GET", "POST"])
def edit_company(id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == "POST":

        if not valid_admin_csrf():
            conn.close()
            flash("The request expired. Please try again.", "danger")
            return redirect(f"/edit_company/{id}")

        company_name = request.form.get("company_name", "").strip()
        drive_date = request.form.get("drive_date", "").strip()

        if not company_name or not drive_date:
            conn.close()
            flash("Company name and drive date are required.", "warning")
            return redirect(f"/edit_company/{id}")

        cur.execute("""
            UPDATE companies
            SET company_name=%s,
                drive_date=%s
            WHERE id=%s
        """, (
            company_name,
            drive_date,
            id
        ))

        conn.commit()
        conn.close()

        flash("Placement Drive Updated Successfully!", "success")

        return redirect("/companies")

    cur.execute("""
        SELECT *
        FROM companies
        WHERE id=%s
    """, (id,))

    company = cur.fetchone()

    if not company:
        conn.close()
        flash("Placement drive not found.", "warning")
        return redirect("/companies")

    conn.close()

    return render_template(
        "edit_company.html",
        company=company,
        csrf_token=admin_csrf_token()
    )

@app.route("/delete_company/<int:id>", methods=["POST"])
def delete_company(id):

    if "admin" not in session:
        return redirect("/login")

    if not valid_admin_csrf():
        flash("The request expired. Please try again.", "danger")
        return redirect("/companies")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT id, company_name FROM companies WHERE id=%s", (id,))
    company = cur.fetchone()

    if not company:
        conn.close()
        flash("Placement drive not found.", "warning")
        return redirect("/companies")

    cur.execute("DELETE FROM companies WHERE id=%s", (id,))
    refresh_student_attendance_totals(cur)
    conn.commit()
    conn.close()

    flash(f"{company['company_name']} and its attendance records were deleted.", "success")

    return redirect("/companies")

@app.route("/companies")
def companies():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # IMPORTANT: This returns rows as dictionaries
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
    SELECT
        id,
        company_name,
        drive_date,
        attendance_marked,

        CASE
            WHEN drive_date < CURDATE()
            THEN 'Completed'
            ELSE 'Upcoming'
        END AS drive_status

    FROM companies

    ORDER BY drive_date DESC
""")

    companies = cur.fetchall()

    conn.close()

    return render_template(
        "companies.html",
        companies=companies,
        csrf_token=admin_csrf_token()
    )

@app.route("/attendance")
def attendance():

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT
            id,
            company_name,
            drive_date,
            attendance_marked
        FROM companies
        ORDER BY drive_date DESC
    """)

    companies = cur.fetchall()

    conn.close()

    return render_template(
        "attendance.html",
        companies=companies
    )

@app.route("/mark_attendance/<int:company_id>", methods=["GET", "POST"])
def mark_attendance(company_id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Get company details
    cur.execute("""
        SELECT *
        FROM companies
        WHERE id=%s
    """, (company_id,))
    company = cur.fetchone()

    # Get all students
    cur.execute("""
        SELECT *
        FROM students
        ORDER BY usn
    """)
    students = cur.fetchall()

    # Save Attendance
    if request.method == "POST":

        for student in students:

            status = request.form.get(str(student["id"]))

            # Check if attendance already exists
            cur.execute("""
                SELECT id
                FROM attendance
                WHERE student_id=%s
                AND company_id=%s
            """, (
                student["id"],
                company_id
            ))

            existing = cur.fetchone()

            if existing:
                continue

            # Save attendance
            cur.execute("""
                INSERT INTO attendance
                (student_id, company_id, status)
                VALUES(%s,%s,%s)
            """, (
                student["id"],
                company_id,
                status
            ))

            # Update missed count
            if status == "Missed":

                cur.execute("""
                    UPDATE students
                    SET missed_companies = missed_companies + 1
                    WHERE id=%s
                """, (student["id"],))

            # Debar student after 5 missed drives
            cur.execute("""
                UPDATE students
                SET debarred = 1
                WHERE id=%s
                AND missed_companies >= 5
            """, (student["id"],))

        # Mark company attendance as completed
        cur.execute("""
            UPDATE companies
            SET attendance_marked = 1
            WHERE id=%s
        """, (company_id,))

        conn.commit()
        conn.close()

        flash("Attendance Saved Successfully", "success")

        return redirect("/attendance")

    conn.close()

    return render_template(
        "mark_attendance.html",
        company=company,
        students=students
    )
    
@app.route("/view_attendance/<int:company_id>")
def view_attendance(company_id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Company Details
    cur.execute("""
        SELECT *
        FROM companies
        WHERE id=%s
    """, (company_id,))

    company = cur.fetchone()

    # Attendance Details
    cur.execute("""
        SELECT
            students.usn,
            students.name,
            students.branch,
            attendance.status
        FROM attendance

        JOIN students
        ON attendance.student_id = students.id

        WHERE attendance.company_id=%s

        ORDER BY students.usn
    """, (company_id,))

    attendance = cur.fetchall()

    conn.close()

    return render_template(
        "view_attendance.html",
        company=company,
        attendance=attendance
    )

@app.route("/save_attendance/<int:company_id>", methods=["POST"])
def save_attendance(company_id):

    if "admin" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # Get all students
    cur.execute("SELECT id FROM students")
    students = cur.fetchall()

    for student in students:

        student_id = student[0]

        status = request.form.get(f"attendance_{student_id}")

        # Save attendance
        cur.execute("""
            INSERT INTO attendance
            (
                student_id,
                company_id,
                status
            )
            VALUES(%s,%s,%s)
        """, (
            student_id,
            company_id,
            status
        ))

        # Count missed drives
        cur.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id=%s
            AND status='Missed'
        """, (student_id,))

        missed = cur.fetchone()[0]

        # Update missed count
        cur.execute("""
            UPDATE students
            SET missed_companies=%s
            WHERE id=%s
        """, (
            missed,
            student_id
        ))

        # Debar after 5 misses
        if missed >= 5:

            cur.execute("""
                UPDATE students
                SET debarred=1
                WHERE id=%s
            """, (student_id,))

        else:

            cur.execute("""
                UPDATE students
                SET debarred=0
                WHERE id=%s
            """, (student_id,))

    conn.commit()
    conn.close()

    flash("Attendance Saved Successfully", "success")

    return redirect("/companies")

@app.route("/logout")
def logout():

    # Remove admin session
    session.pop("admin", None)
    session.pop("admin_csrf_token", None)

    flash("Admin logged out successfully.", "success")

    # Redirect to Home Page
    return redirect("/")


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, port=int(os.getenv("PORT", "8000")))
