from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(f):
    """
    Decorator to ensure user is logged in.
    Redirects to auth.login if no active session is found.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.endpoint))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    """
    Decorator to restrict route access to specific roles.
    Example: @role_required('admin') or @role_required('admin', 'trainer')

    If the user does not possess an allowed role, access is denied.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))

            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("Access denied: You do not have permission to view this page.", "danger")
                # Redirect to user's appropriate landing/dashboard
                if user_role == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif user_role == "trainer":
                    return redirect(url_for("trainer.dashboard"))
                elif user_role == "member":
                    return redirect(url_for("member.dashboard"))
                return redirect(url_for("home"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def approved_required(f):
    """
    Decorator to ensure user account status is 'approved'.
    Members with 'pending' status cannot access protected member areas until approved by an admin.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("status") != "approved":
            flash(
                "Your account registration is currently pending admin verification.",
                "info",
            )
            return redirect(url_for("auth.pending_approval"))
        return f(*args, **kwargs)

    return decorated_function
