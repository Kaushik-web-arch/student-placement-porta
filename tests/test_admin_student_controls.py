import unittest
from datetime import date

import app as portal


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.result = None

    def execute(self, query, params=None):
        sql = " ".join(query.split()).lower()
        params = params or ()

        if "from information_schema.columns" in sql:
            self.result = [(1,)]
        elif "select * from students" in sql and "order by usn" in sql:
            self.result = [student.copy() for student in self.state["students"]]
        elif "select * from students where id=" in sql:
            student = self._by_id(params[0])
            self.result = None if student is None else student.copy()
        elif "select status from attendance" in sql:
            student_id = params[0]
            self.result = [
                {"status": row["status"]}
                for row in self.state["attendance"]
                if row["student_id"] == student_id
            ][-5:]
        elif "select count(*) as total from students where debarred=0" in sql:
            self.result = {"total": sum(not item["debarred"] for item in self.state["students"])}
        elif "select count(*) as total from students where debarred=1" in sql:
            self.result = {"total": sum(bool(item["debarred"]) for item in self.state["students"])}
        elif "select count(*) as total from students" in sql:
            self.result = {"total": len(self.state["students"])}
        elif "select company_name from companies" in sql:
            self.result = {"company_name": "Demo Drive"}
        elif "select * from companies where id=" in sql:
            company = self._company_by_id(params[0])
            self.result = None if company is None else company.copy()
        elif "select id, company_name from companies" in sql:
            company = self._company_by_id(params[0])
            self.result = None if company is None else {
                "id": company["id"], "company_name": company["company_name"]
            }
        elif "from companies left join attendance" in sql:
            student_id = params[0]
            rows = []
            for company in self.state["companies"]:
                record = next((item for item in self.state["attendance"] if item["student_id"] == student_id and item["company_id"] == company["id"]), None)
                rows.append({
                    "id": company["id"], "company_name": company["company_name"],
                    "drive_date": company["drive_date"],
                    "attendance_status": None if record is None else record["status"],
                })
            self.result = rows
        elif "from attendance inner join companies" in sql or "from attendance join companies" in sql:
            student_id = params[0]
            self.result = [
                {
                    "company_name": self._company_by_id(row["company_id"])["company_name"],
                    "drive_date": self._company_by_id(row["company_id"])["drive_date"],
                    "status": row["status"],
                }
                for row in self.state["attendance"]
                if row["student_id"] == student_id and self._company_by_id(row["company_id"])
            ]
        elif "case when drive_date < curdate()" in sql:
            self.result = [dict(company, drive_status="Completed" if company["drive_date"] < date.today() else "Upcoming") for company in self.state["companies"]]
        elif "select id, name, usn from students" in sql:
            self.result = self._by_id(params[0])
        elif "select id, name from students" in sql:
            student = self._by_id(params[0])
            self.result = None if student is None else {"id": student["id"], "name": student["name"]}
        elif "update students set usn=" in sql:
            usn, username, name, email, branch, debarred, student_id = params
            student = self._by_id(student_id)
            student.update(usn=usn, username=username, name=name, email=email, branch=branch, debarred=debarred)
            self.result = None
        elif "update students set password=" in sql and "temporary_password=null" in sql:
            password_hash, student_id = params
            student = self._by_id(student_id)
            student.update(password=password_hash, temporary_password=None, first_login=0)
            self.result = None
        elif "update students set password=" in sql:
            password_hash, temporary_password, student_id = params
            student = self._by_id(student_id)
            student.update(password=password_hash, temporary_password=temporary_password, first_login=1)
            self.result = None
        elif "delete from students" in sql:
            student_id = params[0]
            self.state["students"] = [item for item in self.state["students"] if item["id"] != student_id]
            for key in ("attendance", "feedback", "attempts", "notifications", "results"):
                self.state[key] = [item for item in self.state[key] if item["student_id"] != student_id]
            self.result = None
        elif "select * from students where usn=" in sql:
            self.result = next((item.copy() for item in self.state["students"] if item["usn"] == params[0]), None)
        elif "select id, usn, username, password, first_login from students" in sql:
            student = next((item for item in self.state["students"] if item["username"] == params[0]), None)
            self.result = None if student is None else student.copy()
        elif "update companies set company_name=" in sql:
            company_name, drive_date, company_id = params
            company = self._company_by_id(company_id)
            company.update(company_name=company_name, drive_date=date.fromisoformat(drive_date))
            self.result = None
        elif "delete from companies" in sql:
            company_id = params[0]
            self.state["companies"] = [item for item in self.state["companies"] if item["id"] != company_id]
            self.state["attendance"] = [item for item in self.state["attendance"] if item["company_id"] != company_id]
            self.result = None
        elif "update students as s left join" in sql:
            for student in self.state["students"]:
                missed = sum(item["status"] == "Missed" for item in self.state["attendance"] if item["student_id"] == student["id"])
                student.update(missed_companies=missed, debarred=1 if missed >= 5 else 0)
            self.result = None
        else:
            raise AssertionError(f"Unexpected SQL in test: {sql}")

    def _by_id(self, student_id):
        student = next((item for item in self.state["students"] if item["id"] == student_id), None)
        return None if student is None else student

    def _company_by_id(self, company_id):
        return next((item for item in self.state["companies"] if item["id"] == company_id), None)

    def fetchone(self):
        if isinstance(self.result, list):
            return self.result[0] if self.result else None
        return self.result

    def fetchall(self):
        return self.result if isinstance(self.result, list) else []


class FakeConnection:
    def __init__(self, state):
        self.state = state

    def cursor(self, *_args, **_kwargs):
        return FakeCursor(self.state)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


class AdminStudentControlTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "students": [{
                "id": 1, "usn": "SPP001", "username": "SPP001", "name": "Demo Student",
                "email": "demo@example.com", "branch": "CSE", "password": "hashed",
                "temporary_password": "Temp1234", "first_login": 1,
                "missed_companies": 1, "debarred": 0,
            }],
            "companies": [{"id": 1, "company_name": "Demo Drive", "drive_date": date(2026, 8, 20), "attendance_marked": 1}],
            "attendance": [{"student_id": 1, "company_id": 1, "status": "Missed"}],
            "feedback": [{"student_id": 1}],
            "attempts": [{"student_id": 1}],
            "notifications": [{"student_id": 1}],
            "results": [{"student_id": 1}],
        }
        self.original_connection = portal.get_db_connection
        portal.get_db_connection = lambda: FakeConnection(self.state)
        portal.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = portal.app.test_client()
        with self.client.session_transaction() as session:
            session["admin"] = "admin"
            session["admin_csrf_token"] = "valid-token"

    def tearDown(self):
        portal.get_db_connection = self.original_connection

    def test_students_page_has_password_and_confirmed_delete_controls(self):
        response = self.client.get("/students")
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Temp1234", page)
        self.assertIn("deleteStudentModal", page)
        self.assertIn(">Cancel<", page)
        self.assertIn("/reset_student_password/1", page)

    def test_reset_generates_visible_temporary_password(self):
        response = self.client.post("/reset_student_password/1", data={"csrf_token": "valid-token"})
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(self.state["students"][0]["temporary_password"], "Temp1234")
        self.assertEqual(self.state["students"][0]["first_login"], 1)
        self.assertNotEqual(self.state["students"][0]["password"], "hashed")

    def test_student_private_password_clears_temporary_password(self):
        with self.client.session_transaction() as session:
            session["student"] = "SPP001"
        response = self.client.post("/change_password", data={"new_password": "PrivatePass9"})
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.state["students"][0]["temporary_password"])
        self.assertEqual(self.state["students"][0]["first_login"], 0)

    def test_invalid_csrf_cannot_delete_student(self):
        response = self.client.post("/delete_student/1", data={"csrf_token": "wrong-token"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.state["students"]), 1)

    def test_delete_endpoint_rejects_get_requests(self):
        response = self.client.get("/delete_student/1")
        self.assertEqual(response.status_code, 405)

    def test_delete_removes_account_and_linked_records(self):
        response = self.client.post("/delete_student/1", data={"csrf_token": "valid-token"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.state["students"], [])
        for key in ("attendance", "feedback", "attempts", "notifications", "results"):
            self.assertEqual(self.state[key], [])

        login = self.client.post("/student_login", data={"username": "SPP001", "password": "Temp1234"})
        self.assertEqual(login.status_code, 200)
        self.assertIn("Student access", login.get_data(as_text=True))

    def test_existing_student_session_is_ended_after_deletion(self):
        self.client.post("/delete_student/1", data={"csrf_token": "valid-token"})
        with self.client.session_transaction() as session:
            session["student"] = "SPP001"
        response = self.client.get("/student_dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/student_login"))

    def test_admin_edit_is_immediately_visible_in_student_portal(self):
        response = self.client.post("/edit_student/1", data={
            "csrf_token": "valid-token",
            "usn": "SPP101",
            "name": "Updated Student",
            "email": "updated@example.com",
            "branch": "AIML",
            "status": "active",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.state["students"][0]["username"], "SPP101")

        with self.client.session_transaction() as session:
            session["student_id"] = 1
            session["student"] = "SPP001"
        profile = self.client.get("/student_profile")
        page = profile.get_data(as_text=True)
        self.assertEqual(profile.status_code, 200)
        self.assertIn("Updated Student", page)
        self.assertIn("updated@example.com", page)
        self.assertIn("AIML", page)
        with self.client.session_transaction() as session:
            self.assertEqual(session["student"], "SPP101")

    def test_company_edit_is_visible_in_student_portal(self):
        response = self.client.post("/edit_company/1", data={
            "csrf_token": "valid-token",
            "company_name": "Updated Company",
            "drive_date": "2026-09-15",
        })
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            session["student_id"] = 1
            session["student"] = "SPP001"
            session.pop("_flashes", None)
        drives = self.client.get("/student_companies")
        page = drives.get_data(as_text=True)
        self.assertEqual(drives.status_code, 200)
        self.assertIn("Updated Company", page)
        self.assertIn("2026-09-15", page)

    def test_company_delete_cleans_student_portal_and_recalculates_status(self):
        response = self.client.post("/delete_company/1", data={"csrf_token": "valid-token"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.state["companies"], [])
        self.assertEqual(self.state["attendance"], [])
        self.assertEqual(self.state["students"][0]["missed_companies"], 0)
        self.assertEqual(self.state["students"][0]["debarred"], 0)

        with self.client.session_transaction() as session:
            session["student_id"] = 1
            session["student"] = "SPP001"
            session.pop("_flashes", None)
        drives = self.client.get("/student_companies")
        self.assertEqual(drives.status_code, 200)
        self.assertNotIn("Demo Drive", drives.get_data(as_text=True))

    def test_company_delete_has_cancel_confirmation_and_rejects_get(self):
        page = self.client.get("/companies").get_data(as_text=True)
        self.assertIn("deleteDriveModal", page)
        self.assertIn(">Cancel<", page)
        self.assertEqual(self.client.get("/delete_company/1").status_code, 405)


if __name__ == "__main__":
    unittest.main()
