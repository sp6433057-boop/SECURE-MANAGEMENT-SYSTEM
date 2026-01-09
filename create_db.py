import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DATABASE)
cur = conn.cursor()

# Users table
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Students table
cur.execute("""
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

print("Database initialized successfully")
