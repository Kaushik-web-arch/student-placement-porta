# Student Placement Portal

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap&logoColor=white)

A full-stack placement management application that keeps student records, placement drives, attendance, eligibility, and student access synchronized between dedicated administrator and student portals.

This repository contains the portfolio version maintained and extended by **Kaushik Santhosh**.

## Application preview

![Administrator student profile](docs/screenshots/admin-student-profile.png)

## Why this project exists

Placement information is often distributed across spreadsheets, messages, and manually maintained attendance records. This project brings those workflows into one system so administrators can manage placement activity while students can independently track their profiles, eligibility, and drive history.

## Core features

### Administrator workspace

- Dashboard with student, company, active, and debarred counts
- CSV and Excel-based bulk student onboarding
- Automatically generated temporary student credentials
- Temporary-password reveal and secure password-reset workflow
- Searchable student directory with attendance indicators
- Complete student profile, placement history, and eligibility view
- Student editing for USN, name, email, branch, and status
- Confirmed student deletion with linked-record cleanup
- Placement-drive creation, editing, rescheduling, and deletion
- Drive attendance recording and historical attendance review
- Automatic missed-drive tracking and debarment after five misses

### Student workspace

- Student login with a first-login redirect to password replacement
- Personal dashboard with eligibility and missed-drive progress
- Latest-five-drive attendance tracker
- Placement-drive list with upcoming/completed status
- Personal attendance and placement history
- Profile information synchronized with administrator updates

### Data consistency and safety

- Newly set authentication passwords use Werkzeug hashing; temporary credentials remain readable until replacement
- Student-selected passwords are never shown to administrators
- Only active temporary passwords can be revealed
- Selected administrator edit, reset and delete controls use POST requests and session CSRF tokens
- Deleting a student removes connected attendance, feedback, attempts, notifications, and placement results
- Deleting a drive removes its attendance/history and recalculates student missed-drive totals
- Stable student-session IDs keep both portals synchronized when profile information changes
- Environment credentials and runtime uploads are excluded from version control

## Technology stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, Flask |
| Database | MySQL 8, PyMySQL |
| Data import | pandas, openpyxl, xlrd |
| Frontend | Jinja2, Bootstrap 5, HTML, CSS, JavaScript |
| Security | Werkzeug password hashing, session-based authorization, CSRF tokens |
| Testing | Python `unittest`, Flask test client |

## Project structure

```text
student-placement-portal/
├── app.py                     # Flask routes and application logic
├── database/
│   └── schema.sql             # MySQL schema and relationships
├── sample_data/
│   ├── students_template.csv  # Minimal import template
│   └── students_30_demo.csv   # Fictional 30-student demo dataset
├── static/
│   ├── css/                   # Responsive visual system
│   └── js/                    # Client-side interactions
├── templates/                 # Administrator and student pages
├── tests/                     # Functional regression tests
├── uploads/                   # Runtime files; contents are ignored
├── .env.example               # Safe environment-variable template
└── requirements.txt           # Python dependencies
```

## Local installation

### Prerequisites

- Python 3.12
- MySQL Server 8
- MySQL Workbench
- Git

Python 3.12 is recommended because the pinned dependency range provides reliable Windows wheels for pandas and NumPy.

### 1. Clone the repository

```bash
git clone https://github.com/Kaushik-web-arch/student-placement-porta.git
cd student-placement-porta
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the MySQL database

Open `database/schema.sql` in MySQL Workbench and execute the complete script. It creates the `placement_portal` database, tables, relationships, and local demo administrator.

### 5. Configure environment variables

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Update `.env` with your local MySQL password and a private Flask secret key:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=placement_portal
SECRET_KEY=your_private_random_secret
FLASK_DEBUG=true
PORT=8000
```

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Never commit the generated `.env` file.

### 6. Run the application

```bash
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Local demonstration

The database script includes a local-only administrator account:

```text
Username: admin
Password: admin123
```

Change the demonstration credentials before using the application outside a local development environment.

To test student onboarding, sign in as the administrator and upload `sample_data/students_30_demo.csv`. The records and email addresses in this file are fictional. Save the generated temporary passwords when they are displayed.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

The regression suite covers:

- Student password reset and first-login password replacement
- Student edit synchronization across both portals
- Student deletion and active-session invalidation
- Placement-drive editing and student-side synchronization
- Placement-drive deletion and attendance-total recalculation
- CSRF validation and confirmation controls

The suite contains 11 test methods. Run the command above to establish the result for your checkout.

## Privacy notes

- Do not upload real student spreadsheets or personally identifiable data.
- Do not commit `.env`, MySQL credentials, generated passwords, or runtime uploads.
- The included sample dataset uses fictional records and `example.com` addresses.

## Future improvements

- Role-based administrator permissions
- Email delivery for temporary credentials and drive notifications
- Placement analytics and exportable reports
- Cloud database deployment and production secret management
- CI workflow for automated test execution

## Maintainer

**Kaushik Santhosh**  
Computer Science (Data Science) undergraduate  
GitHub: [Kaushik-web-arch](https://github.com/Kaushik-web-arch)

## Scope and reproducible walkthrough

Eligibility in this version is based on missed-drive/debarment status. Resume upload, CGPA/skills-based matching, advanced placement analytics and automated email delivery are not demonstrated by the current routes.

The tests in [tests/test_admin_student_controls.py](tests/test_admin_student_controls.py) use Flask's test client and a fake database connection. They exercise application behavior but do not replace integration testing against MySQL.

Use a disposable local database and fictional records for this walkthrough:

1. Import the included demo CSV as an administrator and retain one generated temporary credential locally.
2. Sign in as that student, replace the temporary password, and check the profile.
3. Edit the student's name or USN as administrator, then refresh the student workspace to check synchronization.
4. Create a demo drive, record attendance and inspect the student's history.
5. Delete that demo drive and verify attendance totals are recalculated.
6. Delete the demo student and verify the existing student session is rejected.

Record the commit, environment and actual outcomes before describing the walkthrough as passed. The demo CSV is sample input, not evidence of real student adoption.

### Security boundaries

Temporary passwords are stored in readable form until replaced; student-selected passwords are hashed. Legacy plaintext password comparison remains for compatibility. CSRF validation is implemented on selected administrative controls, not every state-changing route. These controls do not establish production security.

## Copyright

© 2026 **Kaushik Santhosh**. All rights reserved.

This repository and its source code are provided publicly for portfolio, educational review, and demonstration purposes. No permission is granted to copy, modify, redistribute, sublicense, or use substantial portions of this project without prior written permission from the copyright holder.
