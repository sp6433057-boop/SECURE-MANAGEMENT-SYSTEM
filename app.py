import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ================= APP CONFIG =================
app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect(DATABASE, timeout=15)
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
            role TEXT NOT NULL DEFAULT 'student'
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
            branch TEXT,
            session TEXT,
            photo TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Please enter email and password")
            return redirect(url_for("login"))

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if not user:
            flash("Invalid email or password")
            return redirect(url_for("login"))

        if not check_password_hash(user["password"], password):
            flash("Invalid email or password")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["user_email"] = user["email"]

        flash("Login successful")

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_profile"))

    return render_template("login.html")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

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
            flash("Email already registered")
            return redirect(url_for("register"))

        except Exception:
            flash("Something went wrong. Try again.")
            return redirect(url_for("register"))

    return render_template("register.html")


# ================= PROMOTE ME =================
@app.route("/promote-me")
def promote_me():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email=?", ("sp6433057@gmail.com",))
    user = cur.fetchone()

    if not user:
        conn.close()
        return "Please register first using this email."

    cur.execute(
        "UPDATE users SET role='admin' WHERE email=?",
        ("sp6433057@gmail.com",)
    )

    conn.commit()
    conn.close()
    return "You are now admin. Logout and login again."


# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        flash("Unauthorized access")
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    conn = get_db()

    if search:
        students = conn.execute("""
            SELECT * FROM students
            WHERE name LIKE ?
               OR roll_number LIKE ?
               OR registration_number LIKE ?
               OR email LIKE ?
               OR branch LIKE ?
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()
    else:
        students = conn.execute("SELECT * FROM students").fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        students=students,
        search=search
    )



# ================= ADMIN PROFILE =================
@app.route("/admin/profile", methods=["GET", "POST"])
def admin_profile():
    if session.get("role") != "admin":
        flash("Unauthorized access")
        return redirect(url_for("login"))

    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name", "")
        department = request.form.get("department", "")
        post = request.form.get("post", "")

        photo = request.files.get("photo")
        filename = None

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        admin = conn.execute(
            "SELECT * FROM admins WHERE email=?",
            (session["user_email"],)
        ).fetchone()

        if admin:
            conn.execute("""
                UPDATE admins
                SET name=?, department=?, post=?, photo=?
                WHERE email=?
            """, (name, department, post, filename, session["user_email"]))
        else:
            conn.execute("""
                INSERT INTO admins (name, department, post, photo, email)
                VALUES (?,?,?,?,?)
            """, (name, department, post, filename, session["user_email"]))

        conn.commit()
        conn.close()
        flash("Profile updated successfully")
        return redirect(url_for("admin_profile"))

    admin = conn.execute(
        "SELECT * FROM admins WHERE email=?",
        (session["user_email"],)
    ).fetchone()
    conn.close()

    return render_template("admin_profile.html", admin=admin)


# ================= ADD STUDENT =================
@app.route("/admin/student/add", methods=["GET", "POST"])
def add_student():
    if session.get("role") != "admin":
        flash("Unauthorized access")
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
                 email, mobile, course, branch, semester, session, photo)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form.get("name"),
                request.form.get("father_name"),
                request.form.get("roll_number"),
                request.form.get("registration_number"),
                request.form.get("email"),
                request.form.get("mobile"),
                request.form.get("course"),
                request.form.get("branch"),
                request.form.get("semester"),
                request.form.get("session"),
                filename
            ))
            conn.commit()
            conn.close()
            flash("Student added successfully")
            return redirect(url_for("admin_dashboard"))

        except sqlite3.IntegrityError:
            flash("Student with this email already exists")
            return redirect(url_for("add_student"))

    return render_template("add_student.html")


# ================= EDIT STUDENT =================
@app.route("/admin/student/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if session.get("role") != "admin":
        flash("Unauthorized access")
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id=?", (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        flash("Student not found")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        conn.execute("""
            UPDATE students SET
            name=?, father_name=?, roll_number=?, registration_number=?,
            email=?, mobile=?, course=?, branch=?, semester=?, session=?
            WHERE id=?
        """, (
            request.form.get("name"),
            request.form.get("father_name"),
            request.form.get("roll_number"),
            request.form.get("registration_number"),
            request.form.get("email"),
            request.form.get("mobile"),
            request.form.get("course"),
            request.form.get("branch"),
            request.form.get("semester"),
            request.form.get("session"),
            student_id
        ))
        conn.commit()
        conn.close()
        flash("Student updated successfully")
        return redirect(url_for("admin_dashboard"))

    conn.close()
    return render_template("edit_student.html", student=student)


# ================= DELETE STUDENT =================
@app.route("/admin/student/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    if session.get("role") != "admin":
        flash("Unauthorized access")
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()
    flash("Student deleted successfully")
    return redirect(url_for("admin_dashboard"))


# ================= STUDENT PROFILE =================
@app.route("/student-profile")
def student_profile():
    if session.get("role") != "student":
        flash("Unauthorized access")
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE email=?",
        (session["user_email"],)
    ).fetchone()
    conn.close()

    if not student:
        return "Student record not found. Contact admin."

    return render_template("student_profile.html", student=student)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for("login"))


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)





