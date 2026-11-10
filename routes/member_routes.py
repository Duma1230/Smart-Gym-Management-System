from datetime import date, datetime
from flask import Blueprint, render_template, session
from utils.decorators import login_required, role_required, approved_required
from utils.db import query_db

member_bp = Blueprint("member", __name__, url_prefix="/member")


@member_bp.route("/dashboard")
@login_required
@role_required("member")
@approved_required
def dashboard():
    """
    Member Dashboard overview:
    - Current active membership with start date, expiry date, days remaining, and status.
    - Payment history with amount, date, payment method, and receipt reference.
    - Assigned personal trainer information.
    - Suitable fallback message if no active membership is assigned.
    """
    member_user_id = session.get("user_id")

    try:
        # 1. Fetch current active or latest membership for this logged-in member
        membership = query_db(
            """
            SELECT m.id, m.start_date, m.end_date, m.status, m.notes, m.created_at,
                   p.plan_name, p.description, p.duration_days, p.price
            FROM memberships m
            JOIN membership_plans p ON m.plan_id = p.id
            WHERE m.member_id = %s
            ORDER BY 
                CASE 
                    WHEN m.status = 'active' THEN 1 
                    WHEN m.status = 'pending_payment' THEN 2 
                    ELSE 3 
                END,
                m.end_date DESC, m.id DESC
            LIMIT 1
            """,
            (member_user_id,),
            one=True,
        )

        # Calculate days remaining for active membership
        days_left = None
        is_expired = False
        today = date.today()

        if membership and membership.get("end_date"):
            end_val = membership["end_date"]
            if isinstance(end_val, str):
                end_dt = datetime.strptime(end_val, "%Y-%m-%d").date()
            elif isinstance(end_val, datetime):
                end_dt = end_val.date()
            else:
                end_dt = end_val

            diff = (end_dt - today).days
            if diff >= 0:
                days_left = diff
            else:
                days_left = 0
                is_expired = True

        # 2. Fetch full payment history for this member
        payments = query_db(
            """
            SELECT py.id, py.amount, py.payment_method, py.payment_date, py.reference_number, py.notes, py.created_at,
                   p.plan_name
            FROM payments py
            JOIN memberships m ON py.membership_id = m.id
            JOIN membership_plans p ON m.plan_id = p.id
            WHERE py.member_id = %s
            ORDER BY py.payment_date DESC, py.id DESC
            """,
            (member_user_id,),
        )

        # 3. Fetch assigned trainer info
        trainer = query_db(
            """
            SELECT t.id, t.full_name, t.email, t.phone, tp.specialization, tp.bio
            FROM member_profiles mp
            JOIN users t ON mp.assigned_trainer_id = t.id
            LEFT JOIN trainer_profiles tp ON t.id = tp.user_id
            WHERE mp.user_id = %s
            """,
            (member_user_id,),
            one=True,
        )

    except Exception as e:
        membership = None
        days_left = None
        is_expired = False
        payments = []
        trainer = None

    return render_template(
        "member/dashboard.html",
        membership=membership,
        days_left=days_left,
        is_expired=is_expired,
        payments=payments,
        trainer=trainer,
    )
