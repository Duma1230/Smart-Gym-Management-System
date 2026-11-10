from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db import query_db, execute_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user authentication for all roles (Admin, Trainer, Member)."""
    if "user_id" in session:
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "trainer":
            return redirect(url_for("trainer.dashboard"))
        elif role == "member":
            return redirect(url_for("member.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html")

        try:
            user = query_db(
                "SELECT id, full_name, email, password_hash, role, status FROM users WHERE email = %s",
                (email,),
                one=True,
            )

            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "danger")
                return render_template("auth/login.html")

            # Check account status
            if user["status"] == "pending":
                session["user_id"] = user["id"]
                session["user_name"] = user["full_name"]
                session["role"] = user["role"]
                session["status"] = user["status"]
                flash("Your account registration is pending Admin verification.", "info")
                return redirect(url_for("auth.pending_approval"))

            if user["status"] in ("rejected", "inactive"):
                flash("Your account is currently disabled or was not approved. Please contact the gym admin.", "danger")
                return render_template("auth/login.html")

            # Set session for approved user
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]
            session["role"] = user["role"]
            session["status"] = user["status"]

            flash(f"Welcome back, {user['full_name']}!", "success")

            # Redirect based on user role
            if user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            elif user["role"] == "trainer":
                return redirect(url_for("trainer.dashboard"))
            elif user["role"] == "member":
                return redirect(url_for("member.dashboard"))
            return redirect(url_for("home"))

        except Exception as e:
            flash(f"Database error during login: {e}", "danger")
            return render_template("auth/login.html")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle Member self-registration. New members start with status 'pending'."""
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender", "")
        date_of_birth = request.form.get("date_of_birth") or None
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()

        # Validation
        if not full_name or not email or not password:
            flash("Full name, email, and password are required.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html")

        try:
            # Check if email is already registered
            existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
            if existing:
                flash("An account with this email address already exists.", "warning")
                return render_template("auth/register.html")

            # Create pending user record
            pwd_hash = generate_password_hash(password)
            user_res = execute_db(
                """
                INSERT INTO users (full_name, email, password_hash, role, status, phone)
                VALUES (%s, %s, %s, 'member', 'pending', %s)
                """,
                (full_name, email, pwd_hash, phone),
            )
            new_user_id = user_res["lastrowid"]

            # Create corresponding member_profile record
            execute_db(
                """
                INSERT INTO member_profiles (user_id, gender, date_of_birth, address, emergency_contact)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (new_user_id, gender if gender else None, date_of_birth, address, emergency_contact),
            )

            flash(
                "Registration successful! Your account is pending Admin approval. You may log in once approved.",
                "success",
            )
            return redirect(url_for("auth.login"))

        except Exception as e:
            flash(f"Error during registration: {e}", "danger")
            return render_template("auth/register.html")

    return render_template("auth/register.html")


@auth_bp.route("/pending-approval")
def pending_approval():
    """Notice page displayed when a member's account is pending Admin verification."""
    return render_template("auth/pending.html")


@auth_bp.route("/logout")
def logout():
    """Clear session data and return to login page."""
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))
