"""
End-to-End Workflow Integration Test
Tests:
1. Member Self-Registration (status defaults to 'pending')
2. Pending Member Login (redirected to pending approval notice)
3. Admin Access Control (unauthenticated/member denied access to approval actions)
4. Admin Member Listing & Status Filtering
5. Admin Member Approval (updates status to 'approved')
6. Approved Member Login (successfully logs in and accesses member dashboard)
7. Admin Member Rejection (updates status to 'rejected')
8. Rejected Member Login Attempt (login blocked with flash error)
"""

import unittest
from werkzeug.security import generate_password_hash, check_password_hash
from app import create_app
import utils.db as db_module
import routes.auth_routes as auth_routes
import routes.admin_routes as admin_routes
import routes.member_routes as member_routes


def _mock_execute_transaction(mock_db, operations):
    """Apply transaction statements to the in-memory test database."""
    results = []
    first_insert_id = None
    for query, args in operations:
        resolved_args = tuple(
            first_insert_id if value == "$FIRST_INSERT_ID" else value
            for value in (args or ())
        )
        result = mock_db.execute(query, resolved_args)
        results.append(result)
        if first_insert_id is None and result.get("lastrowid"):
            first_insert_id = result["lastrowid"]
    return results


class MockDatabase:
    """In-memory mock database store simulating MySQL for deterministic workflow testing."""

    def __init__(self):
        self.users = [
            {
                "id": 1,
                "full_name": "System Administrator",
                "email": "admin@smartgym.com",
                "password_hash": generate_password_hash("Admin@123"),
                "role": "admin",
                "status": "approved",
                "phone": "+1-555-0100",
                "created_at": "2026-11-01 10:00:00",
                "updated_at": "2026-11-01 10:00:00",
            }
        ]
        self.member_profiles = []
        self.membership_plans = [
            {"id": 1, "plan_name": "Monthly Standard", "price": 49.99, "is_active": 1}
        ]
        self.memberships = []
        self.next_user_id = 2
        self.next_profile_id = 1

    def query(self, sql, args=(), one=False):
        sql_clean = " ".join(sql.strip().split())

        # Count queries
        if "SELECT COUNT(*) AS c FROM users WHERE role = 'member'" in sql_clean:
            if "status = 'pending'" in sql_clean:
                count = sum(1 for u in self.users if u["role"] == "member" and u["status"] == "pending")
            elif "status = 'approved'" in sql_clean:
                count = sum(1 for u in self.users if u["role"] == "member" and u["status"] == "approved")
            elif "status = 'rejected'" in sql_clean:
                count = sum(1 for u in self.users if u["role"] == "member" and u["status"] == "rejected")
            else:
                count = sum(1 for u in self.users if u["role"] == "member")
            return {"c": count} if one else [{"c": count}]

        if "SELECT COUNT(*) AS c FROM users WHERE role = 'trainer'" in sql_clean:
            count = sum(1 for u in self.users if u["role"] == "trainer")
            return {"c": count} if one else [{"c": count}]

        if "SELECT COUNT(*) AS c FROM membership_plans" in sql_clean:
            count = len(self.membership_plans)
            return {"c": count} if one else [{"c": count}]

        # User by email
        if "FROM users WHERE email = %s" in sql_clean:
            email = args[0]
            matched = [u for u in self.users if u["email"].lower() == email.lower()]
            return (matched[0] if matched else None) if one else matched

        # User by id and role
        if "FROM users WHERE id = %s AND role = 'member'" in sql_clean:
            uid = args[0]
            matched = [u for u in self.users if u["id"] == uid and u["role"] == "member"]
            return (matched[0] if matched else None) if one else matched

        # Members list query
        if "FROM users u" in sql_clean and "WHERE u.role = 'member'" in sql_clean:
            results = []
            for u in self.users:
                if u["role"] != "member":
                    continue
                # Status filter check
                if "u.status = %s" in sql_clean:
                    status_arg = args[0]
                    if u["status"] != status_arg:
                        continue
                profile = next((p for p in self.member_profiles if p["user_id"] == u["id"]), {})
                results.append({
                    "id": u["id"],
                    "full_name": u["full_name"],
                    "email": u["email"],
                    "phone": u["phone"],
                    "status": u["status"],
                    "created_at": u.get("created_at", "2026-11-09 00:00:00"),
                    "gender": profile.get("gender"),
                    "date_of_birth": profile.get("date_of_birth"),
                    "emergency_contact": profile.get("emergency_contact"),
                    "address": profile.get("address"),
                    "assigned_trainer_name": None,
                })
            return (results[0] if results else None) if one else results

        # Fallback
        return None if one else []

    def execute(self, sql, args=(), commit=True):
        sql_clean = " ".join(sql.strip().split())

        if "INSERT INTO users" in sql_clean:
            full_name, email, pwd_hash, phone = args[0], args[1], args[2], args[3]
            user_id = self.next_user_id
            self.next_user_id += 1
            self.users.append({
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "password_hash": pwd_hash,
                "role": "member",
                "status": "pending",
                "phone": phone,
                "created_at": "2026-11-09 00:00:00",
                "updated_at": "2026-11-09 00:00:00",
            })
            return {"lastrowid": user_id, "rowcount": 1}

        if "INSERT INTO member_profiles" in sql_clean:
            user_id, gender, dob, address, emergency = args[0], args[1], args[2], args[3], args[4]
            self.member_profiles.append({
                "id": self.next_profile_id,
                "user_id": user_id,
                "gender": gender,
                "date_of_birth": dob,
                "address": address,
                "emergency_contact": emergency,
                "assigned_trainer_id": None,
            })
            self.next_profile_id += 1
            return {"lastrowid": self.next_profile_id - 1, "rowcount": 1}

        if "UPDATE users SET status = 'approved'" in sql_clean:
            user_id = args[0]
            for u in self.users:
                if u["id"] == user_id:
                    u["status"] = "approved"
                    return {"lastrowid": user_id, "rowcount": 1}

        if "UPDATE users SET status = 'rejected'" in sql_clean:
            user_id = args[0]
            for u in self.users:
                if u["id"] == user_id:
                    u["status"] = "rejected"
                    return {"lastrowid": user_id, "rowcount": 1}

        return {"lastrowid": 0, "rowcount": 0}


class MemberVerificationWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_db = MockDatabase()

        # Monkey-patch db module and routes directly
        self.modules_to_patch = [db_module, auth_routes, admin_routes, member_routes]
        self.orig_query = {}
        self.orig_exec = {}
        self.orig_transaction = {}

        for mod in self.modules_to_patch:
            if hasattr(mod, "query_db"):
                self.orig_query[mod] = mod.query_db
                mod.query_db = self.mock_db.query
            if hasattr(mod, "execute_db"):
                self.orig_exec[mod] = mod.execute_db
                mod.execute_db = self.mock_db.execute
            if hasattr(mod, "execute_transaction"):
                self.orig_transaction[mod] = mod.execute_transaction
                mod.execute_transaction = lambda operations, db=self.mock_db: _mock_execute_transaction(db, operations)

        self.app = create_app("development")
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def tearDown(self):
        for mod, fn in self.orig_query.items():
            mod.query_db = fn
        for mod, fn in self.orig_exec.items():
            mod.execute_db = fn
        for mod, fn in self.orig_transaction.items():
            mod.execute_transaction = fn

    def test_complete_member_verification_lifecycle(self):
        print("\n--- Starting Member Verification & Management Lifecycle Test ---")

        # -------------------------------------------------------------
        # Step 1: Member Self-Registration
        # -------------------------------------------------------------
        reg_data = {
            "full_name": "Test Member",
            "email": "testmember@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "phone": "+1-555-9999",
            "gender": "male",
            "date_of_birth": "1998-04-12",
            "address": "456 Test Street",
            "emergency_contact": "+1-555-8888",
        }
        res_reg = self.client.post("/auth/register", data=reg_data, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn(b"Registration successful! Your account is pending Admin approval", res_reg.data)

        # Verify in DB: status must be 'pending'
        created_user = next((u for u in self.mock_db.users if u["email"] == "testmember@example.com"), None)
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user["status"], "pending")
        self.assertEqual(created_user["role"], "member")
        member_id = created_user["id"]
        print(f"[PASSED] Step 1: Member registered with ID {member_id} and status 'pending'")

        # -------------------------------------------------------------
        # Step 2: Pending Member Login Attempt
        # -------------------------------------------------------------
        res_login_pending = self.client.post(
            "/auth/login",
            data={"email": "testmember@example.com", "password": "Password@123"},
            follow_redirects=True,
        )
        self.assertEqual(res_login_pending.status_code, 200)
        self.assertIn(b"Registration Pending Approval", res_login_pending.data)
        print("[PASSED] Step 2: Pending member cannot access gym portal, redirected to pending notice")

        # -------------------------------------------------------------
        # Step 3: Security Check - Non-admin cannot approve
        # -------------------------------------------------------------
        # Unauthenticated POST to approve
        res_unauth = self.client.post(f"/admin/members/{member_id}/approve", follow_redirects=False)
        self.assertEqual(res_unauth.status_code, 302)  # Redirected to login
        print("[PASSED] Step 3: Unauthenticated request to /admin/members/<id>/approve blocked")

        # -------------------------------------------------------------
        # Step 4: Admin Login & View Members List
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "System Administrator"
            sess["role"] = "admin"
            sess["status"] = "approved"

        # View all members
        res_members = self.client.get("/admin/members?status=all")
        self.assertEqual(res_members.status_code, 200)
        self.assertIn(b"Test Member", res_members.data)
        self.assertIn(b"testmember@example.com", res_members.data)
        self.assertIn(b"Pending Approval", res_members.data)

        # View pending tab
        res_pending_tab = self.client.get("/admin/members?status=pending")
        self.assertEqual(res_pending_tab.status_code, 200)
        self.assertIn(b"Test Member", res_pending_tab.data)
        print("[PASSED] Step 4: Admin members list displays pending member with details & action buttons")

        # -------------------------------------------------------------
        # Step 5: Admin Approves Member
        # -------------------------------------------------------------
        res_approve = self.client.post(
            f"/admin/members/{member_id}/approve",
            data={"current_status": "pending"},
            follow_redirects=True,
        )
        self.assertEqual(res_approve.status_code, 200)
        self.assertIn(b"has been approved successfully", res_approve.data)
        self.assertEqual(created_user["status"], "approved")
        print(f"[PASSED] Step 5: Admin approved member {member_id}; status updated to 'approved'")

        # -------------------------------------------------------------
        # Step 6: Approved Member Login & Dashboard Access
        # -------------------------------------------------------------
        # Clear admin session
        with self.client.session_transaction() as sess:
            sess.clear()

        res_login_approved = self.client.post(
            "/auth/login",
            data={"email": "testmember@example.com", "password": "Password@123"},
            follow_redirects=True,
        )
        self.assertEqual(res_login_approved.status_code, 200)
        self.assertIn(b"Member Portal", res_login_approved.data)
        self.assertIn(b"Welcome, Test Member", res_login_approved.data)
        print("[PASSED] Step 6: Approved member logged in and successfully accessed Member Portal")

        # -------------------------------------------------------------
        # Step 7: Admin Rejection
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "System Administrator"
            sess["role"] = "admin"
            sess["status"] = "approved"

        res_reject = self.client.post(
            f"/admin/members/{member_id}/reject",
            data={"current_status": "all"},
            follow_redirects=True,
        )
        self.assertEqual(res_reject.status_code, 200)
        self.assertIn(b"registration has been rejected", res_reject.data)
        self.assertEqual(created_user["status"], "rejected")
        print(f"[PASSED] Step 7: Admin rejected member {member_id}; status updated to 'rejected'")

        # -------------------------------------------------------------
        # Step 8: Rejected Member Login Blocked
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess.clear()

        res_login_rejected = self.client.post(
            "/auth/login",
            data={"email": "testmember@example.com", "password": "Password@123"},
            follow_redirects=True,
        )
        self.assertEqual(res_login_rejected.status_code, 200)
        self.assertIn(b"disabled or was not approved", res_login_rejected.data)
        print("[PASSED] Step 8: Rejected member login blocked with warning message")

        print("--- All Member Verification Lifecycle Tests Passed Successfully! ---\n")


    def test_role_protection_for_non_admin(self):
        """Verify that a member cannot access or perform admin approval actions."""
        # Session as normal member
        with self.client.session_transaction() as sess:
            sess["user_id"] = 99
            sess["user_name"] = "Regular Member"
            sess["role"] = "member"
            sess["status"] = "approved"

        # Member attempts to access admin members page
        res_view = self.client.get("/admin/members", follow_redirects=False)
        self.assertEqual(res_view.status_code, 302)  # Denied and redirected

        # Member attempts to approve an account
        res_post = self.client.post("/admin/members/2/approve", follow_redirects=False)
        self.assertEqual(res_post.status_code, 302)  # Denied and redirected
        print("[PASSED] Non-admin member blocked from admin member management routes")


if __name__ == "__main__":
    unittest.main()
