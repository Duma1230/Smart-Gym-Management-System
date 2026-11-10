from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.decorators import login_required, role_required
from utils.db import query_db, execute_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_PAYMENT_METHODS = ["Cash", "Bank Transfer", "Card (POS)", "Cheque"]


# ========================================================
# 1. ADMIN DASHBOARD
# ========================================================
@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    """Admin Dashboard overview."""
    try:
        stats = {
            "total_members": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'member'", one=True)["c"],
            "pending_approvals": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'member' AND status = 'pending'", one=True)["c"],
            "total_trainers": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'trainer'", one=True)["c"],
            "active_plans": query_db("SELECT COUNT(*) AS c FROM membership_plans WHERE is_active = 1", one=True)["c"],
            "total_payments": query_db("SELECT COUNT(*) AS c FROM payments", one=True)["c"],
            "total_revenue": query_db("SELECT COALESCE(SUM(amount), 0) AS total FROM payments", one=True)["total"],
            "pending_memberships": query_db("SELECT COUNT(*) AS c FROM memberships WHERE status = 'pending_payment'", one=True)["c"],
        }
    except Exception:
        stats = {
            "total_members": 0,
            "pending_approvals": 0,
            "total_trainers": 0,
            "active_plans": 0,
            "total_payments": 0,
            "total_revenue": 0.0,
            "pending_memberships": 0,
        }

    return render_template("admin/dashboard.html", stats=stats)


# ========================================================
# 2. MEMBER VERIFICATION & MANAGEMENT
# ========================================================
@admin_bp.route("/members")
@login_required
@role_required("admin")
def members():
    """
    Display all registered members with status filtering (all, pending, approved, rejected)
    and optional text search.
    """
    status_filter = request.args.get("status", "all").strip().lower()
    search_query = request.args.get("q", "").strip()

    try:
        counts = {
            "all": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'member'", one=True)["c"],
            "pending": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'member' AND status = 'pending'", one=True)["c"],
            "approved": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'member' AND status = 'approved'", one=True)["c"],
            "rejected": query_db("SELECT COUNT(*) AS c FROM users WHERE role = 'member' AND status = 'rejected'", one=True)["c"],
        }

        base_query = """
            SELECT 
                u.id,
                u.full_name,
                u.email,
                u.phone,
                u.status,
                u.created_at,
                mp.gender,
                mp.date_of_birth,
                mp.emergency_contact,
                mp.address,
                t.full_name AS assigned_trainer_name,
                (
                    SELECT p.plan_name 
                    FROM memberships m 
                    JOIN membership_plans p ON m.plan_id = p.id 
                    WHERE m.member_id = u.id AND m.status = 'active' 
                    ORDER BY m.id DESC LIMIT 1
                ) AS current_plan_name,
                (
                    SELECT m.status 
                    FROM memberships m 
                    WHERE m.member_id = u.id 
                    ORDER BY m.id DESC LIMIT 1
                ) AS latest_membership_status
            FROM users u
            LEFT JOIN member_profiles mp ON u.id = mp.user_id
            LEFT JOIN users t ON mp.assigned_trainer_id = t.id
            WHERE u.role = 'member'
        """
        params = []

        if status_filter in ("pending", "approved", "rejected"):
            base_query += " AND u.status = %s"
            params.append(status_filter)

        if search_query:
            base_query += " AND (u.full_name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        base_query += " ORDER BY u.created_at DESC"
        members_list = query_db(base_query, tuple(params))

        # Also get active plans for the "Assign Plan" quick modal/dropdown
        active_plans = query_db(
            "SELECT id, plan_name, duration_days, price FROM membership_plans WHERE is_active = 1 ORDER BY price ASC"
        )

    except Exception as e:
        flash(f"Error loading members: {e}", "danger")
        counts = {"all": 0, "pending": 0, "approved": 0, "rejected": 0}
        members_list = []
        active_plans = []

    return render_template(
        "admin/members.html",
        members=members_list,
        counts=counts,
        current_status=status_filter,
        search_query=search_query,
        active_plans=active_plans,
    )


@admin_bp.route("/members/<int:user_id>/approve", methods=["POST"])
@login_required
@role_required("admin")
def approve_member(user_id):
    """Approve a member registration. Updates users.status to 'approved'."""
    try:
        user = query_db(
            "SELECT id, full_name, email, role, status FROM users WHERE id = %s AND role = 'member'",
            (user_id,),
            one=True,
        )

        if not user:
            flash("Member not found.", "danger")
            return redirect(url_for("admin.members"))

        execute_db(
            "UPDATE users SET status = 'approved', updated_at = NOW() WHERE id = %s AND role = 'member'",
            (user_id,),
        )
        flash(f"Member '{user['full_name']}' ({user['email']}) has been approved successfully. They can now log in.", "success")

    except Exception as e:
        flash(f"Error approving member: {e}", "danger")

    return_status = request.form.get("current_status", "all")
    return redirect(url_for("admin.members", status=return_status))


@admin_bp.route("/members/<int:user_id>/reject", methods=["POST"])
@login_required
@role_required("admin")
def reject_member(user_id):
    """Reject a member registration. Updates users.status to 'rejected'."""
    try:
        user = query_db(
            "SELECT id, full_name, email, role, status FROM users WHERE id = %s AND role = 'member'",
            (user_id,),
            one=True,
        )

        if not user:
            flash("Member not found.", "danger")
            return redirect(url_for("admin.members"))

        execute_db(
            "UPDATE users SET status = 'rejected', updated_at = NOW() WHERE id = %s AND role = 'member'",
            (user_id,),
        )
        flash(f"Member '{user['full_name']}' ({user['email']}) registration has been rejected.", "warning")

    except Exception as e:
        flash(f"Error rejecting member: {e}", "danger")

    return_status = request.form.get("current_status", "all")
    return redirect(url_for("admin.members", status=return_status))


# ========================================================
# 3. MEMBERSHIP PLANS MANAGEMENT
# ========================================================
@admin_bp.route("/plans")
@login_required
@role_required("admin")
def plans():
    """Display all available membership plans with enrollment statistics."""
    try:
        plans_list = query_db(
            """
            SELECT p.id, p.plan_name, p.description, p.duration_days, p.price, p.is_active, p.created_at,
                   COUNT(m.id) AS enrolled_count
            FROM membership_plans p
            LEFT JOIN memberships m ON p.id = m.plan_id AND m.status = 'active'
            GROUP BY p.id
            ORDER BY p.is_active DESC, p.price ASC
            """
        )
        total_plans = len(plans_list)
        active_plans = sum(1 for p in plans_list if p["is_active"] == 1)
    except Exception as e:
        flash(f"Error retrieving membership plans: {e}", "danger")
        plans_list = []
        total_plans = 0
        active_plans = 0

    return render_template(
        "admin/plans.html",
        plans=plans_list,
        total_plans=total_plans,
        active_plans=active_plans,
    )


@admin_bp.route("/plans/create", methods=["POST"])
@login_required
@role_required("admin")
def create_plan():
    """Add a new membership plan."""
    plan_name = request.form.get("plan_name", "").strip()
    description = request.form.get("description", "").strip()
    duration_str = request.form.get("duration_days", "").strip()
    price_str = request.form.get("price", "").strip()

    if not plan_name:
        flash("Plan name is required.", "danger")
        return redirect(url_for("admin.plans"))

    try:
        duration_days = int(duration_str)
        if duration_days <= 0:
            raise ValueError()
    except ValueError:
        flash("Duration must be a positive number of days (e.g., 30, 90, 365).", "danger")
        return redirect(url_for("admin.plans"))

    try:
        price = float(price_str)
        if price < 0:
            raise ValueError()
    except ValueError:
        flash("Price must be a valid non-negative number.", "danger")
        return redirect(url_for("admin.plans"))

    try:
        execute_db(
            """
            INSERT INTO membership_plans (plan_name, description, duration_days, price, is_active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (plan_name, description if description else None, duration_days, price),
        )
        flash(f"Membership plan '{plan_name}' has been created successfully!", "success")
    except Exception as e:
        flash(f"Error creating plan: {e}", "danger")

    return redirect(url_for("admin.plans"))


@admin_bp.route("/plans/<int:plan_id>/edit", methods=["POST"])
@login_required
@role_required("admin")
def edit_plan(plan_id):
    """Edit an existing membership plan."""
    plan_name = request.form.get("plan_name", "").strip()
    description = request.form.get("description", "").strip()
    duration_str = request.form.get("duration_days", "").strip()
    price_str = request.form.get("price", "").strip()

    if not plan_name:
        flash("Plan name is required.", "danger")
        return redirect(url_for("admin.plans"))

    try:
        duration_days = int(duration_str)
        if duration_days <= 0:
            raise ValueError()
    except ValueError:
        flash("Duration must be a positive number of days.", "danger")
        return redirect(url_for("admin.plans"))

    try:
        price = float(price_str)
        if price < 0:
            raise ValueError()
    except ValueError:
        flash("Price must be a valid non-negative number.", "danger")
        return redirect(url_for("admin.plans"))

    try:
        execute_db(
            """
            UPDATE membership_plans
            SET plan_name = %s, description = %s, duration_days = %s, price = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (plan_name, description if description else None, duration_days, price, plan_id),
        )
        flash(f"Plan '{plan_name}' updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating plan: {e}", "danger")

    return redirect(url_for("admin.plans"))


@admin_bp.route("/plans/<int:plan_id>/toggle-status", methods=["POST"])
@login_required
@role_required("admin")
def toggle_plan_status(plan_id):
    """Deactivate or reactivate a membership plan."""
    try:
        plan = query_db(
            "SELECT id, plan_name, is_active FROM membership_plans WHERE id = %s",
            (plan_id,),
            one=True,
        )
        if not plan:
            flash("Plan not found.", "danger")
            return redirect(url_for("admin.plans"))

        new_status = 0 if plan["is_active"] == 1 else 1
        status_text = "deactivated" if new_status == 0 else "reactivated"

        execute_db(
            "UPDATE membership_plans SET is_active = %s, updated_at = NOW() WHERE id = %s",
            (new_status, plan_id),
        )
        flash(f"Plan '{plan['plan_name']}' has been {status_text}.", "info")
    except Exception as e:
        flash(f"Error changing plan status: {e}", "danger")

    return redirect(url_for("admin.plans"))


# ========================================================
# 4. ASSIGN MEMBERSHIP PLAN TO MEMBER
# ========================================================
@admin_bp.route("/members/<int:member_id>/assign-plan", methods=["POST"])
@login_required
@role_required("admin")
def assign_plan(member_id):
    """
    Assign a membership plan to a registered and approved member.
    Creates a new membership in 'pending_payment' status until offline payment is recorded.
    """
    plan_id_str = request.form.get("plan_id")
    start_date_str = request.form.get("start_date", "").strip()
    notes = request.form.get("notes", "").strip()

    if not plan_id_str:
        flash("Please select a membership plan.", "danger")
        return redirect(url_for("admin.members"))

    try:
        member = query_db(
            "SELECT id, full_name, status FROM users WHERE id = %s AND role = 'member'",
            (member_id,),
            one=True,
        )
        if not member:
            flash("Member not found.", "danger")
            return redirect(url_for("admin.members"))

        if member["status"] != "approved":
            flash("Only approved members can be assigned a membership plan.", "warning")
            return redirect(url_for("admin.members"))

        plan = query_db(
            "SELECT id, plan_name, duration_days, price FROM membership_plans WHERE id = %s AND is_active = 1",
            (int(plan_id_str),),
            one=True,
        )
        if not plan:
            flash("Selected plan is invalid or deactivated.", "danger")
            return redirect(url_for("admin.members"))

        # Parse start date or default to today
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = date.today()

        end_date = start_date + timedelta(days=plan["duration_days"])

        # Create membership in 'pending_payment' status
        res = execute_db(
            """
            INSERT INTO memberships (member_id, plan_id, start_date, end_date, status, notes)
            VALUES (%s, %s, %s, %s, 'pending_payment', %s)
            """,
            (
                member_id,
                plan["id"],
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                notes if notes else f"Assigned by Admin on {date.today()}",
            ),
        )
        new_membership_id = res["lastrowid"]

        flash(
            f"Plan '{plan['plan_name']}' assigned to {member['full_name']} (Status: Pending Payment). "
            f"Please record the offline payment to activate this membership.",
            "success",
        )
        return redirect(url_for("admin.record_payment", member_id=member_id, membership_id=new_membership_id))

    except Exception as e:
        flash(f"Error assigning membership plan: {e}", "danger")
        return redirect(url_for("admin.members"))


# ========================================================
# 5. OFFLINE PAYMENT MANAGEMENT
# ========================================================
@admin_bp.route("/payments")
@login_required
@role_required("admin")
def payments():
    """Display history of all manually recorded offline payments."""
    method_filter = request.args.get("method", "all").strip()
    search_query = request.args.get("q", "").strip()

    try:
        # Base query for payment records
        base_query = """
            SELECT py.id, py.amount, py.payment_method, py.payment_date, py.reference_number, py.notes, py.created_at,
                   u.id AS member_id, u.full_name AS member_name, u.email AS member_email,
                   p.plan_name,
                   m.id AS membership_id, m.status AS membership_status, m.start_date, m.end_date,
                   admin_user.full_name AS recorded_by_name
            FROM payments py
            JOIN users u ON py.member_id = u.id
            JOIN memberships m ON py.membership_id = m.id
            JOIN membership_plans p ON m.plan_id = p.id
            LEFT JOIN users admin_user ON py.recorded_by_admin_id = admin_user.id
            WHERE 1=1
        """
        params = []

        if method_filter in ALLOWED_PAYMENT_METHODS:
            base_query += " AND py.payment_method = %s"
            params.append(method_filter)

        if search_query:
            base_query += " AND (u.full_name LIKE %s OR u.email LIKE %s OR py.reference_number LIKE %s)"
            search_pat = f"%{search_query}%"
            params.extend([search_pat, search_pat, search_pat])

        base_query += " ORDER BY py.payment_date DESC, py.id DESC"
        payments_list = query_db(base_query, tuple(params))

        # Overall summary stats
        total_rev_res = query_db("SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM payments", one=True)
        total_revenue = total_rev_res["total"] if total_rev_res else 0.0
        total_transactions = total_rev_res["count"] if total_rev_res else 0

        # Pending memberships awaiting payment
        pending_memberships = query_db(
            """
            SELECT m.id, m.start_date, m.end_date, m.status,
                   u.id AS member_id, u.full_name AS member_name, u.email AS member_email,
                   p.plan_name, p.price
            FROM memberships m
            JOIN users u ON m.member_id = u.id
            JOIN membership_plans p ON m.plan_id = p.id
            WHERE m.status = 'pending_payment'
            ORDER BY m.id DESC
            """
        )

    except Exception as e:
        flash(f"Error loading payments: {e}", "danger")
        payments_list = []
        total_revenue = 0.0
        total_transactions = 0
        pending_memberships = []

    return render_template(
        "admin/payments.html",
        payments=payments_list,
        total_revenue=total_revenue,
        total_transactions=total_transactions,
        pending_memberships=pending_memberships,
        current_method=method_filter,
        search_query=search_query,
        allowed_methods=ALLOWED_PAYMENT_METHODS,
    )


@admin_bp.route("/payments/record", methods=["GET", "POST"])
@login_required
@role_required("admin")
def record_payment():
    """
    Record an offline payment (Cash, Bank Transfer, POS Card, Cheque).
    Upon successful payment recording, the corresponding membership is ACTIVATED.
    """
    if request.method == "POST":
        member_id_str = request.form.get("member_id", "").strip()
        membership_id_str = request.form.get("membership_id", "").strip()
        plan_id_str = request.form.get("plan_id", "").strip()
        amount_str = request.form.get("amount", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        payment_date_str = request.form.get("payment_date", "").strip()
        reference_number = request.form.get("reference_number", "").strip()
        notes = request.form.get("notes", "").strip()

        # Validation
        if not member_id_str:
            flash("Please select a gym member.", "danger")
            return redirect(url_for("admin.record_payment"))

        if payment_method not in ALLOWED_PAYMENT_METHODS:
            flash(f"Invalid payment method. Allowed methods: {', '.join(ALLOWED_PAYMENT_METHODS)}", "danger")
            return redirect(url_for("admin.record_payment"))

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            flash("Please enter a valid payment amount greater than zero.", "danger")
            return redirect(url_for("admin.record_payment"))

        # Parse payment date
        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date() if payment_date_str else date.today()
        except ValueError:
            payment_date = date.today()

        admin_id = session.get("user_id")

        try:
            member_id = int(member_id_str)
            member = query_db(
                "SELECT id, full_name, email, status FROM users WHERE id = %s AND role = 'member'",
                (member_id,),
                one=True,
            )
            if not member:
                flash("Member not found.", "danger")
                return redirect(url_for("admin.record_payment"))

            target_membership_id = None

            # Case A: Paying for an existing membership (e.g. pending_payment)
            if membership_id_str and membership_id_str.isdigit():
                m_id = int(membership_id_str)
                existing_m = query_db(
                    "SELECT id, member_id, plan_id, status FROM memberships WHERE id = %s AND member_id = %s",
                    (m_id, member_id),
                    one=True,
                )
                if existing_m:
                    target_membership_id = existing_m["id"]

            # Case B: Direct assignment + payment via selecting a plan
            if not target_membership_id:
                if not plan_id_str or not plan_id_str.isdigit():
                    flash("Please select a membership plan for this payment.", "danger")
                    return redirect(url_for("admin.record_payment", member_id=member_id))

                plan = query_db(
                    "SELECT id, plan_name, duration_days, price FROM membership_plans WHERE id = %s AND is_active = 1",
                    (int(plan_id_str),),
                    one=True,
                )
                if not plan:
                    flash("Selected membership plan not found or inactive.", "danger")
                    return redirect(url_for("admin.record_payment", member_id=member_id))

                start_date = payment_date
                end_date = start_date + timedelta(days=plan["duration_days"])

                # Create membership directly
                res_m = execute_db(
                    """
                    INSERT INTO memberships (member_id, plan_id, start_date, end_date, status, notes)
                    VALUES (%s, %s, %s, %s, 'active', %s)
                    """,
                    (
                        member_id,
                        plan["id"],
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                        f"Created with offline payment on {payment_date}",
                    ),
                )
                target_membership_id = res_m["lastrowid"]

            # 1. Record the Payment in payments table
            execute_db(
                """
                INSERT INTO payments (membership_id, member_id, amount, payment_method, payment_date, reference_number, notes, recorded_by_admin_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    target_membership_id,
                    member_id,
                    amount,
                    payment_method,
                    payment_date.strftime("%Y-%m-%d"),
                    reference_number if reference_number else None,
                    notes if notes else None,
                    admin_id,
                ),
            )

            # 2. Activate the membership!
            execute_db(
                "UPDATE memberships SET status = 'active', updated_at = NOW() WHERE id = %s",
                (target_membership_id,),
            )

            flash(
                f"Offline payment of LKR {amount:,.2f} via {payment_method} recorded successfully! "
                f"Membership for {member['full_name']} is now ACTIVE.",
                "success",
            )
            return redirect(url_for("admin.payments"))

        except Exception as e:
            flash(f"Error recording payment: {e}", "danger")
            return redirect(url_for("admin.record_payment"))

    # GET request - prepare form data
    try:
        approved_members = query_db(
            "SELECT id, full_name, email, phone FROM users WHERE role = 'member' AND status = 'approved' ORDER BY full_name ASC"
        )
        active_plans = query_db(
            "SELECT id, plan_name, duration_days, price FROM membership_plans WHERE is_active = 1 ORDER BY price ASC"
        )
        pending_memberships = query_db(
            """
            SELECT m.id, m.member_id, m.plan_id, m.start_date, m.end_date,
                   u.full_name AS member_name, u.email AS member_email,
                   p.plan_name, p.price
            FROM memberships m
            JOIN users u ON m.member_id = u.id
            JOIN membership_plans p ON m.plan_id = p.id
            WHERE m.status = 'pending_payment'
            ORDER BY m.id DESC
            """
        )
    except Exception as e:
        flash(f"Error loading payment form data: {e}", "danger")
        approved_members = []
        active_plans = []
        pending_memberships = []

    # Check query params for pre-filling
    prefill_member_id = request.args.get("member_id", type=int)
    prefill_membership_id = request.args.get("membership_id", type=int)
    today_date = date.today().strftime("%Y-%m-%d")

    return render_template(
        "admin/record_payment.html",
        members=approved_members,
        plans=active_plans,
        pending_memberships=pending_memberships,
        prefill_member_id=prefill_member_id,
        prefill_membership_id=prefill_membership_id,
        today_date=today_date,
        allowed_methods=ALLOWED_PAYMENT_METHODS,
    )
