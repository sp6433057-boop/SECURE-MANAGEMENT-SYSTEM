import os
import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = "change_this_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

ADMIN_PHOTO_FOLDER = os.path.join("static", "uploads", "admin_photos")
os.makedirs(ADMIN_PHOTO_FOLDER, exist_ok=True)
app.config["ADMIN_PHOTO_FOLDER"] = ADMIN_PHOTO_FOLDER

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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

        flash("Invalid credentials", "error")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] == "admin":
        return redirect(url_for("admin_dashboard"))

    return "Student dashboard later"

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template("admin_dashboard.html")

# ---------------- ADMIN PROFILE ----------------
@app.route("/admin/profile")
def admin_profile():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admins WHERE email = (SELECT email FROM users WHERE id=?)",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("admin_profile.html", admin=admin)

# ---------------- EDIT ADMIN PROFILE ----------------
@app.route("/admin/profile/edit", methods=["GET", "POST"])
def edit_admin_profile():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    email = conn.execute(
        "SELECT email FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()["email"]

    admin = conn.execute(
        "SELECT * FROM admins WHERE email=?",
        (email,)
    ).fetchone()

    if request.method == "POST":
        name = request.form.get("name")
        department = request.form.get("department")
        post = request.form.get("post")

        photo = request.files.get("photo")
        filename = admin["photo"] if admin else None

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["ADMIN_PHOTO_FOLDER"], filename))

        if admin:
            conn.execute("""
                UPDATE admins SET name=?, department=?, post=?, photo=?
                WHERE email=?
            """, (name, department, post, filename, email))
        else:
            conn.execute("""
                INSERT INTO admins (name, department, post, photo, email)
                VALUES (?,?,?,?,?)
            """, (name, department, post, filename, email))

        conn.commit()
        conn.close()
        return redirect(url_for("admin_profile"))

    conn.close()
    return render_template("edit_admin_profile.html", admin=admin)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- RUN (RENDER SAFE) ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
