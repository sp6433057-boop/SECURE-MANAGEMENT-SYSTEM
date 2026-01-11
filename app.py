import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            department TEXT,
            post TEXT,
            photo TEXT,
            email TEXT UNIQUE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            father_name TEXT,
            roll_number TEXT,
            registration_number TEXT,
            email TEXT UNIQUE,
            mobile TEXT,
            course TEXT,
            semester TEXT,
            session TEXT,
            photo TEXT
        )
    """)

    conn.commit()
    conn.close()


# CREATE TABLES ON STARTUP
init_db()


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if not user:
            flash("User not found")
            return redirect(url_for("login"))

        if not check_password_hash(user["password"], password):
            flash("Incorrect password")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["role"] = user["role"]

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("student_profile"))

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            flash("All fields are required")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
                (name, email, hashed_password, "student")
            )
            conn.commit()
            conn.close()

            flash("Registration successful. Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return redirect(url_for("login"))

        except Exception as e:
            print("REGISTER ERROR:", e)
            flash("Something went wrong.")
            return redirect(url_for("register"))

    return render_template("register.html")


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template("admin_dashboard.html", students=students)


# ---------------- ADMIN PROFILE ----------------
@app.route("/admin/profile")
def admin_profile():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admins WHERE email=(SELECT email FROM users WHERE id=?)",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("admin_profile.html", admin=admin)


# ---------------- ADD STUDENT ----------------
@app.route("/admin/student/add", methods=["GET", "POST"])
def add_student():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        photo = request.files.get("photo")
        filename = None

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        try:
            conn = get_db()
            conn.execute("""
                INSERT INTO students
                (name, father_name, roll_number, registration_number,
                 email, mobile, course, semester, session, photo)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get("name"),
                request.form.get("father_name"),
                request.form.get("roll_number"),
                request.form.get("registration_number"),
                request.form.get("email"),
                request.form.get("mobile"),
                request.form.get("course"),
                request.form.get("semester"),
                request.form.get("session"),
                filename
            ))
            conn.commit()
            conn.close()
            flash("Student added successfully")
            return redirect(url_for("admin_dashboard"))

        except sqlite3.IntegrityError:
            conn.close()
            flash("Student with this email already exists")
            return redirect(url_for("add_student"))

    return render_template("add_student.html")


# ---------------- EDIT STUDENT ----------------
@app.route("/admin/student/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id=?", (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        return "Student not found"

    if request.method == "POST":
        filename = student["photo"]
        photo = request.files.get("photo")

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute("""
            UPDATE students SET
            name=?, father_name=?, roll_number=?, registration_number=?,
            email=?, mobile=?, course=?, semester=?, session=?, photo=?
            WHERE id=?
        """, (
            request.form.get("name"),
            request.form.get("father_name"),
            request.form.get("roll_number"),
            request.form.get("registration_number"),
            request.form.get("email"),
            request.form.get("mobile"),
            request.form.get("course"),
            request.form.get("semester"),
            request.form.get("session"),
            filename,
            student_id
        ))

        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("edit_student.html", student=student)


# ---------------- DELETE STUDENT ----------------
@app.route("/admin/student/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# ---------------- STUDENT PROFILE ----------------
@app.route("/student-profile")
def student_profile():
    if session.get("role") != "student":
        return redirect(url_for("login"))

    conn = get_db()
    email = conn.execute(
        "SELECT email FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()["email"]

    student = conn.execute(
        "SELECT * FROM students WHERE email=?", (email,)
    ).fetchone()
    conn.close()

    if not student:
        return "Student record not found. Contact admin."

    return render_template("student_profile.html", student=student)


# ---------------- PROMOTE ME ----------------
@app.route("/promote-me")
def promote_me():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET role='admin' WHERE email=?",
        ("sp6433057@gmail.com",)
    )

    conn.commit()
    conn.close()

    return "You are now an admin. Please log in again."



# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

