"""Student authentication: password hashing, register, login."""
import hashlib
import os
import binascii
from contextlib import closing

from . import db


# ---------- password hashing ----------

def _hash_password(password, salt=None):
    """Return (salt_hex, hash_hex). PBKDF2-SHA256 with 100k iterations."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode()


def _verify_password(password, salt_hex, hash_hex):
    """Return True if password matches the stored hash."""
    try:
        salt = binascii.unhexlify(salt_hex.encode())
    except Exception:
        return False
    _, computed = _hash_password(password, salt)
    return computed == hash_hex


# ---------- schema ----------

_schema_ready = False


def ensure_auth_schema():
    """Add password columns to students table (idempotent)."""
    global _schema_ready
    if _schema_ready:
        return
    with closing(db.get_connection()) as conn:
        for col in ("password_salt", "password_hash"):
            try:
                conn.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")
            except Exception:
                pass
        conn.commit()
    _schema_ready = True


# ---------- register / login ----------

def register_student(name, email, roll_number, password):
    """Create a new student account. Returns (ok, message)."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    roll = (roll_number or "").strip().upper()
    password = password or ""

    if not name or not email or not roll or not password:
        return False, "All fields are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if "@" not in email:
        return False, "Invalid email address."

    ensure_auth_schema()

    with closing(db.get_connection()) as conn:
        # Check existing
        row = conn.execute(
            "SELECT id FROM students WHERE roll_number = ? OR email = ?",
            (roll, email),
        ).fetchone()
        if row:
            return False, "A student with this roll number or email already exists."

        salt, pwd_hash = _hash_password(password)
        conn.execute(
            """INSERT INTO students
               (name, email, roll_number, password_salt, password_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (name, email, roll, salt, pwd_hash),
        )
        conn.commit()

    return True, f"Welcome, {name}! You can now log in."


def login_student(roll_number, password):
    """Verify credentials. Returns (ok, student_dict_or_message)."""
    roll = (roll_number or "").strip().upper()
    password = password or ""
    if not roll or not password:
        return False, "Enter roll number and password."

    ensure_auth_schema()

    with closing(db.get_connection()) as conn:
        row = conn.execute(
            """SELECT id, name, email, roll_number, password_salt, password_hash
               FROM students WHERE roll_number = ?""",
            (roll,),
        ).fetchone()

    if not row:
        return False, "No account found for this roll number."

    if not row["password_hash"]:
        return False, "This account has no password set. Ask admin to reset."

    if not _verify_password(password, row["password_salt"], row["password_hash"]):
        return False, "Incorrect password."

    return True, {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "roll_number": row["roll_number"],
    }

def admin_reset_password(roll_number, new_password):
    """Force-reset a student's password (admin only).
    Returns (ok, message)."""
    roll = (roll_number or "").strip().upper()
    new_password = new_password or ""

    if not roll or not new_password:
        return False, "Roll number and new password are required."
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."

    ensure_auth_schema()

    with closing(db.get_connection()) as conn:
        # Check if student exists
        row = conn.execute(
            "SELECT id, name FROM students WHERE roll_number = ?",
            (roll,),
        ).fetchone()
        
        if not row:
            return False, f"No student found with roll number '{roll}'."

        # Hash the new password
        salt, pwd_hash = _hash_password(new_password)

        # Update the database
        conn.execute(
            """UPDATE students 
               SET password_salt = ?, password_hash = ? 
               WHERE roll_number = ?""",
            (salt, pwd_hash, roll),
        )
        conn.commit()

    return True, f"✅ Password for {row['name']} ({roll}) reset successfully."