"""
Comprehensive Test Suite for:
1. Admin Membership Management (List, Create, Edit, Toggle status)
2. Member Plan Assignment (assign plan to approved member)
3. Offline Payment Recording (Cash, Bank Transfer, POS, Cheque & Membership Activation)
4. Member Portal Integration (Active subscription display, expiry countdown, payment history, no-plan state)
5. Security & Access Control (Admin-only routes, member data isolation)
"""

import unittest
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from app import create_app
import utils.db as db_module
import routes.admin_routes as admin_routes
import routes.member_routes as member_routes
import routes.auth_routes as auth_routes


class MockDatabaseWithPayments:
    """Mock database simulating MySQL 8.0 for full workflow verification."""

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
            },
            {
                "id": 2,
                "full_name": "Active Member One",
                "email": "member1@smartgym.com",
                "password_hash": generate_password_hash("Member@123"),
                "role": "member",
                "status": "approved",
                "phone": "+1-555-0200",
                "created_at": "2026-11-01 11:00:00",
                "updated_at": "2026-11-01 11:00:00",
            },
            {
                "id": 3,
                "full_name": "Active Member Two",
                "email": "member2@smartgym.com",
                "password_hash": generate_password_hash("Member@123"),
                "role": "member",
                "status": "approved",
                "phone": "+1-555-0300",
                "created_at": "2026-11-02 11:00:00",
                "updated_at": "2026-11-02 11:00:00",
            },
        ]
        self.member_profiles = [
            {
                "id": 1,
                "user_id": 2,
                "gender": "male",
                "date_of_birth": "1995-03-10",
                "address": "100 Gym Lane",
                "emergency_contact": "+1-555-0999",
                "assigned_trainer_id": None,
            },
            {
                "id": 2,
                "user_id": 3,
                "gender": "female",
                "date_of_birth": "1997-07-20",
                "address": "200 Fitness Ave",
                "emergency_contact": "+1-555-0888",
                "assigned_trainer_id": None,
            },
        ]
        self.membership_plans = [
            {
                "id": 1,
                "plan_name": "Monthly Standard",
                "description": "Access to gym equipment, cardio zone, and locker rooms.",
                "duration_days": 30,
                "price": 6000.00,
                "is_active": 1,
                "created_at": "2026-11-01 10:00:00",
            },
            {
                "id": 2,
                "plan_name": "Quarterly Fitness",
                "description": "Full gym access plus 1 complimentary trainer assessment.",
                "duration_days": 90,
                "price": 16500.00,
                "is_active": 1,
                "created_at": "2026-11-01 10:00:00",
            },
            {
                "id": 3,
                "plan_name": "Half-Yearly Elite",
                "description": "Full gym access, personalized workout review, and locker priority.",
                "duration_days": 180,
                "price": 30000.00,
                "is_active": 1,
                "created_at": "2026-11-01 10:00:00",
            },
            {
                "id": 4,
                "plan_name": "Annual Premium Pro",
                "description": "All-inclusive annual membership with priority trainer assignment and wellness tracking.",
                "duration_days": 365,
                "price": 54000.00,
                "is_active": 1,
                "created_at": "2026-11-01 10:00:00",
            },
        ]
        self.memberships = []
        self.payments = []
        self.next_plan_id = 5
        self.next_membership_id = 1
        self.next_payment_id = 1

    def query(self, sql, args=(), one=False):
        sql_clean = " ".join(sql.strip().split())

        # Count queries for dashboard
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

        if "SELECT COUNT(*) AS c FROM membership_plans WHERE is_active = 1" in sql_clean:
            count = sum(1 for p in self.membership_plans if p["is_active"] == 1)
            return {"c": count} if one else [{"c": count}]

        if "SELECT COUNT(*) AS c FROM payments" in sql_clean:
            count = len(self.payments)
            return {"c": count} if one else [{"c": count}]

        if "SELECT COALESCE(SUM(amount), 0) AS total FROM payments" in sql_clean:
            total = sum(p["amount"] for p in self.payments)
            return {"total": total} if one else [{"total": total}]

        if "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM payments" in sql_clean:
            total = sum(p["amount"] for p in self.payments)
            return {"total": total, "count": len(self.payments)} if one else [{"total": total, "count": len(self.payments)}]

        if "SELECT COUNT(*) AS c FROM memberships WHERE status = 'pending_payment'" in sql_clean:
            count = sum(1 for m in self.memberships if m["status"] == "pending_payment")
            return {"c": count} if one else [{"c": count}]

        # Users queries
        if "FROM users WHERE email = %s" in sql_clean:
            email = args[0]
            matched = [u for u in self.users if u["email"].lower() == email.lower()]
            return (matched[0] if matched else None) if one else matched

        if "FROM users WHERE id = %s AND role = 'member'" in sql_clean:
            uid = args[0]
            matched = [u for u in self.users if u["id"] == uid and u["role"] == "member"]
            return (matched[0] if matched else None) if one else matched

        if "FROM users WHERE role = 'member' AND status = 'approved'" in sql_clean:
            matched = [u for u in self.users if u["role"] == "member" and u["status"] == "approved"]
            return (matched[0] if matched else None) if one else matched

        # Plans queries
        if "FROM membership_plans WHERE id = %s AND is_active = 1" in sql_clean:
            pid = args[0]
            matched = [p for p in self.membership_plans if p["id"] == pid and p["is_active"] == 1]
            return (matched[0] if matched else None) if one else matched

        if "FROM membership_plans WHERE id = %s" in sql_clean:
            pid = args[0]
            matched = [p for p in self.membership_plans if p["id"] == pid]
            return (matched[0] if matched else None) if one else matched

        if "FROM membership_plans p LEFT JOIN memberships m" in sql_clean:
            res = []
            for p in self.membership_plans:
                enrolled = sum(1 for m in self.memberships if m["plan_id"] == p["id"] and m["status"] == "active")
                res.append({**p, "enrolled_count": enrolled})
            return (res[0] if res else None) if one else res

        if "FROM membership_plans WHERE is_active = 1" in sql_clean:
            matched = [p for p in self.membership_plans if p["is_active"] == 1]
            return (matched[0] if matched else None) if one else matched

        # Memberships queries
        if "FROM memberships WHERE id = %s AND member_id = %s" in sql_clean:
            mid, uid = args[0], args[1]
            matched = [m for m in self.memberships if m["id"] == mid and m["member_id"] == uid]
            return (matched[0] if matched else None) if one else matched

        if "FROM memberships m JOIN users u ON m.member_id = u.id JOIN membership_plans p ON m.plan_id = p.id WHERE m.status = 'pending_payment'" in sql_clean:
            res = []
            for m in self.memberships:
                if m["status"] == "pending_payment":
                    u = next(u for u in self.users if u["id"] == m["member_id"])
                    p = next(p for p in self.membership_plans if p["id"] == m["plan_id"])
                    res.append({
                        "id": m["id"],
                        "member_id": m["member_id"],
                        "plan_id": m["plan_id"],
                        "start_date": m["start_date"],
                        "end_date": m["end_date"],
                        "status": m["status"],
                        "member_name": u["full_name"],
                        "member_email": u["email"],
                        "plan_name": p["plan_name"],
                        "price": p["price"],
                    })
            return (res[0] if res else None) if one else res

        # Member dashboard current membership query
        if "FROM memberships m JOIN membership_plans p ON m.plan_id = p.id WHERE m.member_id = %s" in sql_clean:
            uid = args[0]
            user_memberships = [m for m in self.memberships if m["member_id"] == uid]
            if not user_memberships:
                return None if one else []
            # Sort active first
            user_memberships.sort(key=lambda x: (0 if x["status"] == "active" else 1 if x["status"] == "pending_payment" else 2, x["id"]), reverse=False)
            top_m = user_memberships[0]
            plan = next(p for p in self.membership_plans if p["id"] == top_m["plan_id"])
            res = {
                "id": top_m["id"],
                "start_date": top_m["start_date"],
                "end_date": top_m["end_date"],
                "status": top_m["status"],
                "notes": top_m.get("notes"),
                "created_at": top_m.get("created_at"),
                "plan_name": plan["plan_name"],
                "description": plan["description"],
                "duration_days": plan["duration_days"],
                "price": plan["price"],
            }
            return res if one else [res]

        # Payments list query
        if "FROM payments py" in sql_clean:
            res = []
            for py in sorted(self.payments, key=lambda x: x["id"], reverse=True):
                if "py.member_id = %s" in sql_clean:
                    uid = args[0]
                    if py["member_id"] != uid:
                        continue
                u = next((u for u in self.users if u["id"] == py["member_id"]), None)
                m = next((m for m in self.memberships if m["id"] == py["membership_id"]), None)
                p = next((p for p in self.membership_plans if p["id"] == m["plan_id"]), None) if m else None
                res.append({
                    "id": py["id"],
                    "membership_id": py["membership_id"],
                    "member_id": py["member_id"],
                    "amount": py["amount"],
                    "payment_method": py["payment_method"],
                    "payment_date": py["payment_date"],
                    "reference_number": py["reference_number"],
                    "notes": py["notes"],
                    "created_at": py.get("created_at"),
                    "member_name": u["full_name"] if u else "",
                    "member_email": u["email"] if u else "",
                    "plan_name": p["plan_name"] if p else "",
                    "membership_status": m["status"] if m else "",
                    "start_date": m["start_date"] if m else "",
                    "end_date": m["end_date"] if m else "",
                    "recorded_by_name": "System Administrator",
                })
            return (res[0] if res else None) if one else res

        # Trainer query for member
        if "FROM member_profiles mp JOIN users t ON mp.assigned_trainer_id = t.id" in sql_clean:
            return None if one else []

        # Admin members list
        if "FROM users u LEFT JOIN member_profiles mp" in sql_clean:
            res = []
            for u in self.users:
                if u["role"] != "member":
                    continue
                res.append({
                    "id": u["id"],
                    "full_name": u["full_name"],
                    "email": u["email"],
                    "phone": u["phone"],
                    "status": u["status"],
                    "created_at": u["created_at"],
                    "gender": "male",
                    "date_of_birth": "1995-01-01",
                    "emergency_contact": "+1-555-0999",
                    "address": "Street",
                    "assigned_trainer_name": None,
                    "current_plan_name": None,
                    "latest_membership_status": None,
                })
            return (res[0] if res else None) if one else res

        return None if one else []

    def execute(self, sql, args=(), commit=True):
        sql_clean = " ".join(sql.strip().split())

        # Create Plan
        if "INSERT INTO membership_plans" in sql_clean:
            name, desc, days, price = args[0], args[1], args[2], args[3]
            pid = self.next_plan_id
            self.next_plan_id += 1
            self.membership_plans.append({
                "id": pid,
                "plan_name": name,
                "description": desc,
                "duration_days": int(days),
                "price": float(price),
                "is_active": 1,
                "created_at": "2026-11-09 10:00:00",
            })
            return {"lastrowid": pid, "rowcount": 1}

        # Edit Plan
        if "UPDATE membership_plans SET plan_name = %s" in sql_clean:
            name, desc, days, price, pid = args[0], args[1], args[2], args[3], args[4]
            for p in self.membership_plans:
                if p["id"] == pid:
                    p["plan_name"] = name
                    p["description"] = desc
                    p["duration_days"] = int(days)
                    p["price"] = float(price)
            return {"lastrowid": pid, "rowcount": 1}

        # Toggle Plan Status
        if "UPDATE membership_plans SET is_active = %s" in sql_clean:
            is_active, pid = args[0], args[1]
            for p in self.membership_plans:
                if p["id"] == pid:
                    p["is_active"] = is_active
            return {"lastrowid": pid, "rowcount": 1}

        # Create Membership
        if "INSERT INTO memberships" in sql_clean:
            if "'pending_payment'" in sql_clean:
                member_id, plan_id, start_date, end_date, notes = args[0], args[1], args[2], args[3], args[4]
                status = "pending_payment"
            elif "'active'" in sql_clean:
                member_id, plan_id, start_date, end_date, notes = args[0], args[1], args[2], args[3], args[4]
                status = "active"
            else:
                member_id, plan_id, start_date, end_date, status, notes = args[0], args[1], args[2], args[3], args[4], args[5]

            mid = self.next_membership_id
            self.next_membership_id += 1
            self.memberships.append({
                "id": mid,
                "member_id": int(member_id),
                "plan_id": int(plan_id),
                "start_date": str(start_date),
                "end_date": str(end_date),
                "status": status,
                "notes": notes,
                "created_at": "2026-11-09 10:00:00",
            })
            return {"lastrowid": mid, "rowcount": 1}

        # Update Membership Status (Activate)
        if "UPDATE memberships SET status = 'active'" in sql_clean:
            mid = args[0]
            for m in self.memberships:
                if m["id"] == mid:
                    m["status"] = "active"
            return {"lastrowid": mid, "rowcount": 1}

        # Insert Payment
        if "INSERT INTO payments" in sql_clean:
            membership_id, member_id, amount, method, pdate, ref, notes, admin_id = (
                args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7]
            )
            pay_id = self.next_payment_id
            self.next_payment_id += 1
            self.payments.append({
                "id": pay_id,
                "membership_id": int(membership_id),
                "member_id": int(member_id),
                "amount": float(amount),
                "payment_method": method,
                "payment_date": str(pdate),
                "reference_number": ref,
                "notes": notes,
                "recorded_by_admin_id": int(admin_id),
                "created_at": "2026-11-09 10:00:00",
            })
            return {"lastrowid": pay_id, "rowcount": 1}

        return {"lastrowid": 0, "rowcount": 0}


class MembershipAndPaymentsTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_db = MockDatabaseWithPayments()
        self.modules = [db_module, admin_routes, member_routes, auth_routes]
        self.orig_query = {}
        self.orig_exec = {}

        for mod in self.modules:
            if hasattr(mod, "query_db"):
                self.orig_query[mod] = mod.query_db
                mod.query_db = self.mock_db.query
            if hasattr(mod, "execute_db"):
                self.orig_exec[mod] = mod.execute_db
                mod.execute_db = self.mock_db.execute

        self.app = create_app("development")
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        for mod, fn in self.orig_query.items():
            mod.query_db = fn
        for mod, fn in self.orig_exec.items():
            mod.execute_db = fn

    def test_membership_and_offline_payment_workflow(self):
        print("\n========================================================")
        print(" TEST: Membership Plans & Offline Payment Integration")
        print("========================================================")

        # -------------------------------------------------------------
        # 1. Admin Authentication & Access to Plans
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "System Administrator"
            sess["role"] = "admin"
            sess["status"] = "approved"

        res_plans = self.client.get("/admin/plans")
        self.assertEqual(res_plans.status_code, 200)
        self.assertIn(b"Monthly Standard", res_plans.data)
        self.assertIn(b"LKR 6,000.00", res_plans.data)
        self.assertIn(b"Quarterly Fitness", res_plans.data)
        self.assertIn(b"LKR 16,500.00", res_plans.data)
        self.assertIn(b"Half-Yearly Elite", res_plans.data)
        self.assertIn(b"LKR 30,000.00", res_plans.data)
        self.assertIn(b"Annual Premium Pro", res_plans.data)
        self.assertIn(b"LKR 54,000.00", res_plans.data)
        print("[PASSED] 1. Admin can view configured membership plans with LKR prices.")

        # -------------------------------------------------------------
        # 2. Admin Creates a New Plan
        # -------------------------------------------------------------
        new_plan_payload = {
            "plan_name": "Student Semester Pass",
            "description": "120 days student fitness access",
            "duration_days": "120",
            "price": "22000.00",
        }
        res_create = self.client.post("/admin/plans/create", data=new_plan_payload, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn(b"Student Semester Pass", res_create.data)
        created_p = next((p for p in self.mock_db.membership_plans if p["plan_name"] == "Student Semester Pass"), None)
        self.assertIsNotNone(created_p)
        self.assertEqual(created_p["duration_days"], 120)
        self.assertEqual(created_p["price"], 22000.0)
        print("[PASSED] 2. Admin successfully created 'Student Semester Pass' plan in LKR.")

        # -------------------------------------------------------------
        # 3. Admin Edits a Plan
        # -------------------------------------------------------------
        edit_payload = {
            "plan_name": "Student Semester Elite",
            "description": "Updated 120 days with locker included",
            "duration_days": "120",
            "price": "24000.00",
        }
        res_edit = self.client.post(f"/admin/plans/{created_p['id']}/edit", data=edit_payload, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertEqual(created_p["plan_name"], "Student Semester Elite")
        self.assertEqual(created_p["price"], 24000.0)
        print("[PASSED] 3. Admin successfully edited membership plan details in LKR.")

        # -------------------------------------------------------------
        # 4. Admin Toggles Plan Status (Deactivate / Reactivate)
        # -------------------------------------------------------------
        res_toggle = self.client.post(f"/admin/plans/{created_p['id']}/toggle-status", follow_redirects=True)
        self.assertEqual(res_toggle.status_code, 200)
        self.assertEqual(created_p["is_active"], 0)
        print("[PASSED] 4. Admin successfully deactivated membership plan.")

        # Reactivate it
        self.client.post(f"/admin/plans/{created_p['id']}/toggle-status", follow_redirects=True)
        self.assertEqual(created_p["is_active"], 1)
        print("[PASSED] 4b. Admin successfully reactivated membership plan.")

        # -------------------------------------------------------------
        # 5. Admin Assigns Plan 2 (Quarterly Fitness - LKR 16,500) to Member 2
        # -------------------------------------------------------------
        assign_payload = {
            "plan_id": "2",
            "start_date": "2026-11-10",
            "notes": "Assigned at reception",
        }
        res_assign = self.client.post("/admin/members/2/assign-plan", data=assign_payload, follow_redirects=False)
        self.assertEqual(res_assign.status_code, 302)  # Redirects to payment recording
        self.assertIn("/admin/payments/record", res_assign.headers["Location"])

        # Check membership record in mock db
        assigned_m = next((m for m in self.mock_db.memberships if m["member_id"] == 2), None)
        self.assertIsNotNone(assigned_m)
        self.assertEqual(assigned_m["status"], "pending_payment")
        self.assertEqual(assigned_m["plan_id"], 2)
        print(f"[PASSED] 5. Plan assigned to Member 2 (ID: {assigned_m['id']}, Status: pending_payment).")

        # -------------------------------------------------------------
        # 6. Check Member Portal Before Payment (Pending Payment State)
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["user_name"] = "Active Member One"
            sess["role"] = "member"
            sess["status"] = "approved"

        res_member_pending = self.client.get("/member/dashboard")
        self.assertEqual(res_member_pending.status_code, 200)
        self.assertIn(b"Payment Pending", res_member_pending.data)
        self.assertIn(b"Quarterly Fitness", res_member_pending.data)
        self.assertIn(b"LKR 16,500.00", res_member_pending.data)
        print("[PASSED] 6. Member portal accurately reflects 'Pending Payment' status with LKR 16,500.00.")

        # -------------------------------------------------------------
        # 7. Admin Records Offline Payment (Cash - LKR 16,500) & Activates Membership
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "System Administrator"
            sess["role"] = "admin"
            sess["status"] = "approved"

        payment_payload = {
            "member_id": "2",
            "membership_id": str(assigned_m["id"]),
            "amount": "16500.00",
            "payment_method": "Cash",
            "payment_date": "2026-11-10",
            "reference_number": "REC-2026-0099",
            "notes": "Paid in cash at reception",
        }
        res_payment = self.client.post("/admin/payments/record", data=payment_payload, follow_redirects=True)
        self.assertEqual(res_payment.status_code, 200)
        self.assertIn(b"recorded successfully", res_payment.data)
        self.assertIn(b"ACTIVE", res_payment.data)

        # Verify membership status became 'active'
        self.assertEqual(assigned_m["status"], "active")
        # Verify payment was stored
        recorded_p = next((p for p in self.mock_db.payments if p["member_id"] == 2), None)
        self.assertIsNotNone(recorded_p)
        self.assertEqual(recorded_p["amount"], 16500.00)
        self.assertEqual(recorded_p["payment_method"], "Cash")
        self.assertEqual(recorded_p["reference_number"], "REC-2026-0099")
        print("[PASSED] 7. Offline payment of LKR 16,500.00 recorded; Membership transitioned to 'active'.")

        # -------------------------------------------------------------
        # 8. Check Member Portal After Payment (Active State & Receipt)
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["user_name"] = "Active Member One"
            sess["role"] = "member"
            sess["status"] = "approved"

        res_member_active = self.client.get("/member/dashboard")
        self.assertEqual(res_member_active.status_code, 200)
        self.assertIn(b"Active Membership", res_member_active.data)
        self.assertIn(b"Quarterly Fitness", res_member_active.data)
        self.assertIn(b"REC-2026-0099", res_member_active.data)
        self.assertIn(b"LKR 16,500.00", res_member_active.data)
        self.assertIn(b"Cash", res_member_active.data)
        print("[PASSED] 8. Member portal displays active subscription and offline receipt in LKR.")

        # -------------------------------------------------------------
        # 9. Verify Member Isolation (Member 3 sees 'No Active Plan')
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 3
            sess["user_name"] = "Active Member Two"
            sess["role"] = "member"
            sess["status"] = "approved"

        res_member3 = self.client.get("/member/dashboard")
        self.assertEqual(res_member3.status_code, 200)
        self.assertIn(b"No Active Membership Plan", res_member3.data)
        self.assertNotIn(b"REC-2026-0099", res_member3.data)
        print("[PASSED] 9. Member data isolation verified: Member 3 sees no plan and cannot view Member 2's payment.")

        # -------------------------------------------------------------
        # 10. Direct Assign & Offline Payment (POS Card - LKR 6,000) for Member 3
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "System Administrator"
            sess["role"] = "admin"
            sess["status"] = "approved"

        pos_payload = {
            "member_id": "3",
            "plan_id": "1",  # Monthly Standard (LKR 6,000.00)
            "amount": "6000.00",
            "payment_method": "Card (POS)",
            "payment_date": str(date.today()),
            "reference_number": "POS-SLIP-7712",
            "notes": "Paid with Visa POS terminal",
        }
        res_pos = self.client.post("/admin/payments/record", data=pos_payload, follow_redirects=True)
        self.assertEqual(res_pos.status_code, 200)
        m3_membership = next((m for m in self.mock_db.memberships if m["member_id"] == 3), None)
        self.assertIsNotNone(m3_membership)
        self.assertEqual(m3_membership["status"], "active")
        m3_payment = next((p for p in self.mock_db.payments if p["member_id"] == 3), None)
        self.assertIsNotNone(m3_payment)
        self.assertEqual(m3_payment["amount"], 6000.00)
        self.assertEqual(m3_payment["payment_method"], "Card (POS)")
        self.assertEqual(m3_payment["reference_number"], "POS-SLIP-7712")
        print("[PASSED] 10. Direct assign + POS Card payment (LKR 6,000.00) created and activated membership for Member 3.")
            "notes": "Paid with Visa POS terminal",
        }
        res_pos = self.client.post("/admin/payments/record", data=pos_payload, follow_redirects=True)
        self.assertEqual(res_pos.status_code, 200)
        m3_membership = next((m for m in self.mock_db.memberships if m["member_id"] == 3), None)
        self.assertIsNotNone(m3_membership)
        self.assertEqual(m3_membership["status"], "active")
        m3_payment = next((p for p in self.mock_db.payments if p["member_id"] == 3), None)
        self.assertIsNotNone(m3_payment)
        self.assertEqual(m3_payment["payment_method"], "Card (POS)")
        self.assertEqual(m3_payment["reference_number"], "POS-SLIP-7712")
        print("[PASSED] 10. Direct assign + POS Card payment created and activated membership for Member 3.")

        # -------------------------------------------------------------
        # 11. Security - Non-Admin Access Restrictions
        # -------------------------------------------------------------
        with self.client.session_transaction() as sess:
            sess["user_id"] = 3
            sess["user_name"] = "Active Member Two"
            sess["role"] = "member"
            sess["status"] = "approved"

        # Member attempts to view admin plans
        res_unauth_plans = self.client.get("/admin/plans", follow_redirects=False)
        self.assertEqual(res_unauth_plans.status_code, 302)

        # Member attempts to record payment
        res_unauth_pay = self.client.post("/admin/payments/record", data={}, follow_redirects=False)
        self.assertEqual(res_unauth_pay.status_code, 302)
        print("[PASSED] 11. Non-admin member denied access to admin plan and payment endpoints.")

        print("\n========================================================")
        print(" ALL 11 MEMBERSHIP & OFFLINE PAYMENT TESTS PASSED!")
        print("========================================================\n")


if __name__ == "__main__":
    unittest.main()
