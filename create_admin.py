"""
CLI Utility to securely create the initial System Administrator account.
Usage:
    python create_admin.py
    python create_admin.py --name "Admin Name" --email "admin@example.com"
"""

import sys
import getpass
from werkzeug.security import generate_password_hash
from utils.db import query_db, execute_db, check_db_connection


def create_admin():
    print("==================================================")
    print(" Smart Gym Management System - Admin Setup Utility")
    print("==================================================")

    # 1. Check database connectivity first
    db_ok, msg = check_db_connection()
    if not db_ok:
        print(f"\n[ERROR] Could not connect to MySQL database.")
        print(f"Details: {msg}")
        print("\nPlease ensure MySQL is running, 'smart_gym_db' is created,")
        print("and your .env database credentials are correct.")
        sys.exit(1)

    print(f"\n[OK] {msg}\n")

    # 2. Gather admin details
    full_name = input("Enter Admin Full Name: ").strip()
    if not full_name:
        print("[ERROR] Full name cannot be empty.")
        sys.exit(1)

    email = input("Enter Admin Email: ").strip().lower()
    if not email or "@" not in email:
        print("[ERROR] A valid email address is required.")
        sys.exit(1)

    # 3. Check if user already exists
    existing = query_db("SELECT id, role FROM users WHERE email = %s", (email,), one=True)
    if existing:
        print(f"\n[WARNING] A user with email '{email}' already exists (Role: {existing['role']}).")
        choice = input("Do you want to promote/update this user to Admin? (y/N): ").strip().lower()
        if choice != "y":
            print("Operation aborted.")
            sys.exit(0)

        password = getpass.getpass("Enter New Password (min 6 chars): ")
        confirm_pwd = getpass.getpass("Confirm New Password: ")
        if password != confirm_pwd:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)
        if len(password) < 6:
            print("[ERROR] Password must be at least 6 characters.")
            sys.exit(1)

        hashed = generate_password_hash(password)
        execute_db(
            "UPDATE users SET full_name = %s, password_hash = %s, role = 'admin', status = 'approved' WHERE id = %s",
            (full_name, hashed, existing["id"]),
        )
        print(f"\n[SUCCESS] User '{email}' has been updated to Administrator with approved status!")
        return

    # 4. New Admin password prompt
    password = getpass.getpass("Enter Admin Password (min 6 chars): ")
    confirm_pwd = getpass.getpass("Confirm Admin Password: ")
    if password != confirm_pwd:
        print("[ERROR] Passwords do not match.")
        sys.exit(1)
    if len(password) < 6:
        print("[ERROR] Password must be at least 6 characters.")
        sys.exit(1)

    phone = input("Enter Phone Number (optional): ").strip() or None

    # 5. Insert new Admin
    hashed_pwd = generate_password_hash(password)
    res = execute_db(
        """
        INSERT INTO users (full_name, email, password_hash, role, status, phone)
        VALUES (%s, %s, %s, 'admin', 'approved', %s)
        """,
        (full_name, email, hashed_pwd, phone),
    )

    print("\n==================================================")
    print(f"[SUCCESS] Admin account created successfully!")
    print(f"User ID   : {res['lastrowid']}")
    print(f"Full Name : {full_name}")
    print(f"Email     : {email}")
    print(f"Role      : admin")
    print(f"Status    : approved")
    print("==================================================")
    print("You can now log in using these credentials at /auth/login\n")


if __name__ == "__main__":
    create_admin()
