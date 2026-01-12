import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DATABASE)
cur = conn.cursor()

# USERS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# ADMINS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    department TEXT,
    post TEXT,
    photo TEXT,
    email TEXT UNIQUE
)
""")

# STUDENTS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    father_name TEXT,
    roll_number TEXT,
    registration_number TEXT,
    email TEXT UNIQUE,
    mobile TEXT,
    course TEXT,
    branch TEXT,
    semester TEXT,
    session TEXT,
    photo TEXT
)
""")

conn.commit()
conn.close()

print("Database tables ensured successfully")


