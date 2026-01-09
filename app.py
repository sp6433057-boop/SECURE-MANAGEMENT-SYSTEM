import os
import sqlite3
import re
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = "change_this_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Ensure tables exist
def ensure_tables():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            father_name TEXT,
            roll_number TEXT,
            registration_number TEXT,
            email TEXT,
            mobile TEXT,
            course TEXT,
            semester TEXT,
            photo TEXT
        )
    """)
    conn.commit()
    conn.close()

ensure_tables()

# ---------------- PASSWORD CHECK ----------------
def strong_password(password):
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[^A-Za-z0-9]", password)
    )

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST", "HEAD"])
def login():
    if request.method == "HEAD":
        return "", 200

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not strong_password(password):
            flash("Password must be strong", "error")
            return redirect(url_for("register"))

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(password), "student")
            )
            conn.commit()
            conn.close()
            flash("Registration successful", "success")
            return redirect(url_for("login"))
        except:
            flash("Email already exists", "error")

    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return redirect("/admin" if session["role"] == "admin" else "/student-profile")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template("admin_dashboard.html", students=students)

# ---------------- ADD STUDENT ----------------
@app.route("/add-student", methods=["GET", "POST"])
def add_student():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        data = (
            request.form.get("name"),
            request.form.get("father_name"),
            request.form.get("roll_number"),
            request.form.get("registration_number"),
            request.form.get("email"),
            request.form.get("mobile"),
            request.form.get("course"),
            request.form.get("semester")
        )

        photo = request.files.get("photo")
        filename = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db()
        conn.execute("""
            INSERT INTO students
            (name,father_name,roll_number,registration_number,email,mobile,course,semester,photo)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, data + (filename,))
        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    return render_template("add_student.html")

# ---------------- EXCEL UPLOAD ----------------
@app.route("/upload-excel", methods=["GET", "POST"])
def upload_excel():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        df = pd.read_excel(request.files["excel"])
        conn = get_db()
        for _, r in df.iterrows():
            conn.execute("""
                INSERT INTO students
                (name,father_name,roll_number,registration_number,email,mobile,course,semester)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                r["Name"], r["Father Name"], r["Roll Number"],
                r["Registration Number"], r["Email"],
                r["Mobile"], r["Course"], r["Semester"]
            ))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))

    return render_template("upload_excel.html")

# ---------------- STUDENT PROFILE ----------------
@app.route("/student-profile")
def student_profile():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    conn = get_db()

    # Fetch student details using logged-in user's email
    student = conn.execute(
        """
        SELECT * FROM students 
        WHERE email = (
            SELECT email FROM users WHERE id = ?
        )
        """,
        (session["user_id"],)
    ).fetchone()

    conn.close()

    if not student:
        return "Student record not found. Please contact admin."

    return render_template("student_profile.html", student=student)


# ---------------- TEMP ADMIN ROUTE (USE ONCE) ----------------
@app.route("/make-admin")
def make_admin():
    conn = get_db()
    conn.execute(
        "UPDATE users SET role='admin' WHERE email='sp6433057@gmail.com'"
    )
    conn.commit()
    conn.close()
    return "You are now admin. Please logout and login again."

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- RUN (RENDER SAFE) ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

