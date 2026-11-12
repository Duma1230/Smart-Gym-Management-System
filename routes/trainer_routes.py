from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from utils.decorators import login_required, role_required
from utils.db import query_db, execute_db, execute_transaction

trainer_bp = Blueprint("trainer", __name__, url_prefix="/trainer")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _owned_member(member_id):
    return query_db("""
        SELECT u.id,u.full_name,u.email
        FROM users u JOIN member_profiles mp ON mp.user_id=u.id
        WHERE u.id=%s AND u.role='member' AND mp.assigned_trainer_id=%s
    """, (member_id, session.get("user_id")), one=True)


@trainer_bp.route("/dashboard")
@login_required
@role_required("trainer")
def dashboard():
    tid = session["user_id"]
    members = query_db("""
        SELECT u.id,u.full_name,u.email,u.phone
        FROM member_profiles mp JOIN users u ON u.id=mp.user_id
        WHERE mp.assigned_trainer_id=%s AND u.status='approved' ORDER BY u.full_name
    """, (tid,))
    return render_template("trainer/dashboard.html", members=members, assigned_count=len(members))


@trainer_bp.route("/members/<int:member_id>/workouts", methods=["GET", "POST"])
@login_required
@role_required("trainer")
def workouts(member_id):
    member = _owned_member(member_id)
    if not member:
        flash("This member is not assigned to you.", "danger")
        return redirect(url_for("trainer.dashboard"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        goal = request.form.get("goal", "").strip()
        try:
            start = datetime.strptime(request.form.get("start_date", ""), "%Y-%m-%d").date()
            end_raw = request.form.get("end_date", "").strip()
            end = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else None
            exercise = request.form.get("exercise_name", "").strip()
            day = request.form.get("day_of_week", "Monday")
            sets = int(request.form.get("sets", "3"))
            reps = request.form.get("reps", "10-12").strip()
            if not title or not exercise or day not in DAYS or sets < 1 or not reps or (end and end < start):
                raise ValueError()
            execute_transaction([
                ("""INSERT INTO workout_plans
                    (member_id,trainer_id,title,goal,start_date,end_date,status,notes)
                    VALUES (%s,%s,%s,%s,%s,%s,'active',%s)""",
                 (member_id,session["user_id"],title,goal or None,start,end,request.form.get("notes","").strip() or None)),
                ("""INSERT INTO workout_plan_items
                    (workout_plan_id,day_of_week,exercise_name,sets,reps,instructions,order_index)
                    VALUES (%s,%s,%s,%s,%s,%s,1)""",
                 ("$FIRST_INSERT_ID",day,exercise,sets,reps,request.form.get("instructions","").strip() or None))
            ])
            flash("Workout plan created.", "success")
            return redirect(url_for("trainer.workouts", member_id=member_id))
        except (ValueError, InvalidOperation):
            flash("Check the workout dates, exercise, day, sets and repetitions.", "danger")
        except Exception:
            current_app.logger.exception("Workout plan creation failed")
            flash("Could not save the workout plan. Check the terminal for details.", "danger")

    plans = query_db(
        "SELECT * FROM workout_plans WHERE member_id=%s AND trainer_id=%s ORDER BY created_at DESC",
        (member_id, session["user_id"])
    )
    for plan in plans:
        plan["items"] = query_db("SELECT * FROM workout_plan_items WHERE workout_plan_id=%s ORDER BY FIELD(day_of_week,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),order_index,id",
                                 (plan["id"],))
    return render_template("trainer/workouts.html", member=member, plans=plans, days=DAYS, today=date.today().isoformat())


@trainer_bp.route("/workouts/<int:plan_id>/status", methods=["POST"])
@login_required
@role_required("trainer")
def workout_status(plan_id):
    plan = query_db("SELECT id,member_id FROM workout_plans WHERE id=%s AND trainer_id=%s",
                    (plan_id,session["user_id"]), one=True)
    status = request.form.get("status")
    if plan and status in ("active","completed","archived"):
        execute_db("UPDATE workout_plans SET status=%s WHERE id=%s", (status,plan_id))
        flash("Workout status updated.", "success")
        return redirect(url_for("trainer.workouts", member_id=plan["member_id"]))
    flash("Workout plan not found or invalid status.", "danger")
    return redirect(url_for("trainer.dashboard"))


@trainer_bp.route("/workouts/<int:plan_id>/delete", methods=["POST"])
@login_required
@role_required("trainer")
def delete_workout(plan_id):
    plan = query_db("SELECT id,member_id FROM workout_plans WHERE id=%s AND trainer_id=%s",
                    (plan_id,session["user_id"]), one=True)
    if plan:
        execute_db("DELETE FROM workout_plans WHERE id=%s AND trainer_id=%s", (plan_id,session["user_id"]))
        flash("Workout plan deleted.", "success")
        return redirect(url_for("trainer.workouts", member_id=plan["member_id"]))
    flash("Workout plan not found.", "danger")
    return redirect(url_for("trainer.dashboard"))


@trainer_bp.route("/members/<int:member_id>/progress", methods=["GET", "POST"])
@login_required
@role_required("trainer")
def progress(member_id):
    member = _owned_member(member_id)
    if not member:
        flash("This member is not assigned to you.", "danger")
        return redirect(url_for("trainer.dashboard"))
    if request.method == "POST":
        try:
            recorded = datetime.strptime(request.form.get("recorded_date",""), "%Y-%m-%d").date()
            weight = Decimal(request.form.get("weight_kg",""))
            if weight <= 0 or weight > 500:
                raise ValueError()
            def optional_decimal(key, maximum):
                raw=request.form.get(key,"").strip()
                if not raw: return None
                value=Decimal(raw)
                if value < 0 or value > maximum: raise ValueError()
                return value
            body=optional_decimal("body_fat_percentage",100)
            chest=optional_decimal("chest_cm",300)
            waist=optional_decimal("waist_cm",300)
            biceps=optional_decimal("biceps_cm",150)
            execute_db("""INSERT INTO fitness_progress
                (member_id,trainer_id,recorded_date,weight_kg,body_fat_percentage,chest_cm,waist_cm,biceps_cm,trainer_remarks)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (member_id,session["user_id"],recorded,weight,body,chest,waist,biceps,
                 request.form.get("trainer_remarks","").strip() or None))
            flash("Fitness progress saved.", "success")
        except (ValueError, InvalidOperation):
            flash("Enter a valid date and measurement values.", "danger")
        except Exception:
            flash("Could not save fitness progress.", "danger")
        return redirect(url_for("trainer.progress", member_id=member_id))
    history=query_db("SELECT * FROM fitness_progress WHERE member_id=%s AND trainer_id=%s ORDER BY recorded_date DESC,id DESC",
                     (member_id,session["user_id"]))
    return render_template("trainer/progress.html", member=member, history=history, today=date.today().isoformat())


@trainer_bp.route("/workouts/<int:plan_id>/edit", methods=["POST"])
@login_required
@role_required("trainer")
def edit_workout(plan_id):
    plan = query_db("SELECT id,member_id FROM workout_plans WHERE id=%s AND trainer_id=%s",
                    (plan_id,session["user_id"]), one=True)
    if not plan:
        flash("Workout plan not found.", "danger")
        return redirect(url_for("trainer.dashboard"))
    title=request.form.get("title","").strip()
    goal=request.form.get("goal","").strip()
    try:
        start=datetime.strptime(request.form.get("start_date",""),"%Y-%m-%d").date()
        end_raw=request.form.get("end_date","").strip()
        end=datetime.strptime(end_raw,"%Y-%m-%d").date() if end_raw else None
        if not title or (end and end < start): raise ValueError()
        execute_db("""UPDATE workout_plans SET title=%s,goal=%s,start_date=%s,end_date=%s,notes=%s
                      WHERE id=%s AND trainer_id=%s""",
                   (title,goal or None,start,end,request.form.get("notes","").strip() or None,
                    plan_id,session["user_id"]))
        flash("Workout plan details updated.", "success")
    except ValueError:
        flash("Enter a valid title and date range.", "danger")
    return redirect(url_for("trainer.workouts",member_id=plan["member_id"]))


@trainer_bp.route("/workouts/<int:plan_id>/items/add", methods=["POST"])
@login_required
@role_required("trainer")
def add_workout_item(plan_id):
    plan=query_db("SELECT id,member_id FROM workout_plans WHERE id=%s AND trainer_id=%s",
                  (plan_id,session["user_id"]),one=True)
    if not plan:
        flash("Workout plan not found.", "danger")
        return redirect(url_for("trainer.dashboard"))
    name=request.form.get("exercise_name","").strip()
    day=request.form.get("day_of_week","")
    reps=request.form.get("reps","").strip()
    try:
        sets=int(request.form.get("sets","3"))
        if not name or day not in DAYS or not reps or sets<1 or sets>30: raise ValueError()
        execute_db("""INSERT INTO workout_plan_items
            (workout_plan_id,day_of_week,exercise_name,sets,reps,instructions,order_index)
            VALUES (%s,%s,%s,%s,%s,%s,1)""",
            (plan_id,day,name,sets,reps,request.form.get("instructions","").strip() or None))
        flash("Exercise added to workout plan.", "success")
    except ValueError:
        flash("Enter valid exercise details.", "danger")
    return redirect(url_for("trainer.workouts",member_id=plan["member_id"]))


@trainer_bp.route("/workout-items/<int:item_id>/edit", methods=["POST"])
@login_required
@role_required("trainer")
def edit_workout_item(item_id):
    item=query_db("""SELECT i.id,p.member_id FROM workout_plan_items i
                     JOIN workout_plans p ON p.id=i.workout_plan_id
                     WHERE i.id=%s AND p.trainer_id=%s""",(item_id,session["user_id"]),one=True)
    if not item:
        flash("Exercise not found.", "danger")
        return redirect(url_for("trainer.dashboard"))
    name=request.form.get("exercise_name","").strip()
    day=request.form.get("day_of_week","")
    reps=request.form.get("reps","").strip()
    try:
        sets=int(request.form.get("sets","3"))
        if not name or day not in DAYS or not reps or sets<1 or sets>30: raise ValueError()
        execute_db("""UPDATE workout_plan_items SET exercise_name=%s,day_of_week=%s,sets=%s,reps=%s,instructions=%s
                      WHERE id=%s""",
                   (name,day,sets,reps,request.form.get("instructions","").strip() or None,item_id))
        flash("Exercise updated.", "success")
    except ValueError:
        flash("Enter valid exercise details.", "danger")
    return redirect(url_for("trainer.workouts",member_id=item["member_id"]))


@trainer_bp.route("/workout-items/<int:item_id>/delete", methods=["POST"])
@login_required
@role_required("trainer")
def delete_workout_item(item_id):
    item=query_db("""SELECT i.id,p.member_id FROM workout_plan_items i
                     JOIN workout_plans p ON p.id=i.workout_plan_id
                     WHERE i.id=%s AND p.trainer_id=%s""",(item_id,session["user_id"]),one=True)
    if item:
        execute_db("DELETE FROM workout_plan_items WHERE id=%s",(item_id,))
        flash("Exercise removed.", "success")
        return redirect(url_for("trainer.workouts",member_id=item["member_id"]))
    flash("Exercise not found.", "danger")
    return redirect(url_for("trainer.dashboard"))
