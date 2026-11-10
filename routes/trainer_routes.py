from flask import Blueprint, render_template, session
from utils.decorators import login_required, role_required
from utils.db import query_db

trainer_bp = Blueprint("trainer", __name__, url_prefix="/trainer")


@trainer_bp.route("/dashboard")
@login_required
@role_required("trainer")
def dashboard():
    """Trainer Dashboard overview foundation."""
    trainer_user_id = session.get("user_id")
    try:
        assigned_count = query_db(
            "SELECT COUNT(*) AS c FROM member_profiles WHERE assigned_trainer_id = %s",
            (trainer_user_id,),
            one=True,
        )["c"]
    except Exception:
        assigned_count = 0

    return render_template("trainer/dashboard.html", assigned_count=assigned_count)
