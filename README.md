# Smart Gym Membership & Fitness Management System

A web-based gym management application built with **Python Flask**, **Jinja2**, and **MySQL 8.0**. Designed for academic project submission with clear role-based access control for **Admins**, **Trainers**, and **Members**.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.14.3 / Flask 3.1
- **Database**: MySQL 8.0.46 (Database name: `smart_gym_db`)
- **Frontend**: HTML5, CSS3 (Modern Dark Slate Athletic Theme), Vanilla JavaScript
- **Security**: Werkzeug password hashing (scrypt), HTTP-only sessions, parameterized SQL queries

---

## 📁 Project Architecture & Structure

```text
smart-gym-management/
│
├── app.py                      # Application entry point & factory
├── config.py                   # Configuration classes loading from .env
├── create_admin.py             # CLI utility to securely set up the initial Admin
├── requirements.txt            # Python dependencies
├── .env                        # Local environment variables (DB credentials, secret key)
├── .env.example                # Example environment file template
├── README.md                   # Documentation and setup instructions
│
├── database/
│   ├── schema.sql              # Normalized MySQL schema (10 tables, constraints, indexes)
│   └── sample_data.sql         # Safe sample records for development & testing
│
├── routes/                     # Blueprint controllers
│   ├── auth_routes.py          # Unified login, member registration, logout
│   ├── admin_routes.py         # Member verification, plans, payments, attendance
│   ├── trainer_routes.py       # Assigned members, workout plans, progress updates
│   └── member_routes.py        # Member dashboard, workouts, progress, history
│
├── utils/
│   ├── db.py                   # MySQL connection helper and parameterized query utilities
│   └── decorators.py           # Role-based access decorators (@role_required, @login_required)
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern athletic design system
│   ├── js/
│   │   └── main.js             # Alert auto-dismiss and form validation
│   └── img/                    # Static image directory
│
└── templates/                  # Jinja2 templates
    ├── base.html               # Master layout with navbar and flash messages
    ├── index.html              # Public landing page
    ├── auth/                   # Authentication & registration views
    │   ├── login.html
    │   ├── register.html
    │   └── pending.html
    ├── admin/                  # Admin portal views
    │   ├── dashboard.html
    │   ├── members.html
    │   ├── plans.html
    │   ├── payments.html
    │   └── record_payment.html
    ├── trainer/                # Trainer portal views
    │   └── dashboard.html
    ├── member/                 # Member portal views
    │   └── dashboard.html
    └── errors/                 # Error pages (403, 404, 500)
```

---

## 🗄️ Database Setup in MySQL Workbench

Follow these steps to set up `smart_gym_db` using **MySQL Workbench**:

### Step 1: Open MySQL Workbench
1. Launch **MySQL Workbench**.
2. Connect to your local MySQL 8.0 instance (usually `Local instance MySQL80` on port `3306`).

### Step 2: Import the Database Schema
1. In the top menu, go to **File** &rarr; **Open SQL Script...** (or press `Ctrl + Shift + O`).
2. Navigate to your project folder:
   ```text
   database/schema.sql
   ```
3. Click the **Execute (Lightning Bolt ⚡)** button to run the script.
4. Refresh the **Schemas** panel on the left. You will now see `smart_gym_db` with all **10 tables**:
   - `users`
   - `trainer_profiles`
   - `member_profiles`
   - `membership_plans`
   - `memberships`
   - `payments`
   - `attendance`
   - `workout_plans`
   - `workout_plan_items`
   - `fitness_progress`

### Step 3 (Optional): Load Sample Data
To test the system immediately with pre-configured plans and test accounts:
1. In MySQL Workbench, open:
   ```text
   database/sample_data.sql
   ```
2. Click the **Execute ⚡** button.

---

## ⚙️ Environment Configuration

Check the `.env` file in the project root directory and update your MySQL credentials if your MySQL root account has a password:

```env
# Flask Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=dev-secret-key-smart-gym-management-system-2026

# MySQL Connection Details
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=smart_gym_db
DB_USER=root
DB_PASSWORD=your_mysql_password_here
```

---

## 👤 Initial Admin Account Creation

You can create an Administrator account securely using the included CLI helper:

```powershell
.\venv\Scripts\python.exe create_admin.py
```

Follow the prompts to enter your name, email, and password. The script will securely hash the password and set status to `approved`.

### Default Sample Accounts (if `sample_data.sql` was loaded):
| Role | Email | Password | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin@smartgym.com` | `Admin@123` | `approved` | System Administrator |
| **Trainer** | `john.trainer@smartgym.com` | `Trainer@123` | `approved` | Assigned coach |
| **Member** | `sarah.member@smartgym.com` | `Member@123` | `approved` | Active member with plan |
| **Member** | `mike.pending@smartgym.com` | `Member@123` | `pending` | Test approval workflow |

---

## 🚀 Running the Application

1. Make sure your virtual environment is active:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. Start the Flask application:
   ```powershell
   python app.py
   ```
   *(or `.\venv\Scripts\python.exe app.py`)*
3. Open your browser and visit:
   - **Main Website**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
   - **System Health & DB Diagnostic**: [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health)
   - **Login**: [http://127.0.0.1:5000/auth/login](http://127.0.0.1:5000/auth/login)
   - **Member Self-Registration**: [http://127.0.0.1:5000/auth/register](http://127.0.0.1:5000/auth/register)

---

## 🧪 Running Automated Tests

Run the full end-to-end integration test suite:

```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```

Tests verify:
- Member self-registration with default `pending` status.
- Admin member approval & rejection workflow.
- Membership plan CRUD and status toggles.
- Plan assignment to members.
- Offline payment recording (Cash, Bank Transfer, POS, Cheque) and automatic membership activation.
- Member portal active plan display, expiry countdown, payment history, and user isolation.
- Role-based security access protections.

---

## 🔒 Security & Academic Viva Highlights

- **Password Security**: Scrypt hashing via Werkzeug (`generate_password_hash` / `check_password_hash`). Plaintext passwords are never saved.
- **SQL Injection Prevention**: All queries in `utils/db.py` use parameterized queries (`%s` placeholders passed as separate parameter tuples).
- **Access Control**: Role enforcement via custom decorators (`@role_required('admin')`, `@approved_required`). Members cannot navigate to admin routes simply by typing the URL.
- **Pending Verification Rule**: Self-registered members default to `pending` status. They cannot access the gym portal until verified by an Admin.
- **Offline Payment Modeling**: Payments are recorded manually against distinct `memberships` records to ensure multi-cycle renewal history is accurately preserved without data duplication.
