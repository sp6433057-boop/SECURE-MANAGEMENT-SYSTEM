import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

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

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

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
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
                (name, email, password, "student")
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered. Please login.")
            return redirect(url_for("login"))

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

# ---------------- EDIT STUDENT ----------------
@app.route("/admin/student/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE id=?", (student_id,)
    ).fetchone()

    if request.method == "POST":
        photo = request.files.get("photo")
        filename = student["photo"]

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn.execute("""
            UPDATE students SET
            name=?, father_name=?, roll_number=?, registration_number=?,
            email=?, mobile=?, course=?, semester=?, photo=?
            WHERE id=?
        """, (
            request.form["name"],
            request.form["father_name"],
            request.form["roll_number"],
            request.form["registration_number"],
            request.form["email"],
            request.form["mobile"],
            request.form["course"],
            request.form["semester"],
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

    return render_template("student_profile.html", student=student)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)

