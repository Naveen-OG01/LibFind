from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from libfind import db, auth
import os
import streamlit as st

# Bridge Render Environment Variables to Streamlit Secrets for the DB to work
os.environ["TURSO_DATABASE_URL"] = os.environ.get("TURSO_DATABASE_URL", "")
os.environ["TURSO_AUTH_TOKEN"] = os.environ.get("TURSO_AUTH_TOKEN", "")

# Manually set Streamlit secrets (since we aren't running Streamlit UI)
try:
    st.secrets["TURSO_DATABASE_URL"] = os.environ["TURSO_DATABASE_URL"]
    st.secrets["TURSO_AUTH_TOKEN"] = os.environ["TURSO_AUTH_TOKEN"]
except Exception:
    pass


app = FastAPI(title="LibFind API", description="Backend API for the LibFind Library System")

# Allow your future React website to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow everything since it's a college project
    allow_credentials=False, # MUST be false when origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Request Bodies ---
class LoginRequest(BaseModel):
    roll_number: str
    password: str

class BorrowRequest(BaseModel):
    student_id: int
    book_id: int
    loan_days: int = 14

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the LibFind API!"}

@app.get("/api/books")
def get_books():
    """Get a list of all books in the library."""
    books = db.get_all_books()
    return books

@app.get("/api/books/search")
def search_books(q: str = "", category: Optional[str] = None):
    """Search for books by title, author, or category."""
    from libfind import search
    results = search.search_books(q, field="all", category=category)
    return results

@app.post("/api/login")
def login(req: LoginRequest):
    """Login a student and return their details."""
    ok, result = auth.login_student(req.roll_number, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=result)
    return {"message": "Login successful", "student": result}

@app.post("/api/borrow")
def borrow_book(req: BorrowRequest):
    """Borrow a book for a student."""
    # Get student info
    student = db.get_student_by_roll(str(req.student_id)) 
    if not student:
        # Fallback if student_id is actually the primary key ID
        student = db.get_student_by_roll(str(req.student_id)) # Simplified for demo
    
    # Call your existing DB logic
    ok, result = db.borrow_book(
        student_name="API User", # We can update this to fetch actual name
        student_email="api@test.com",
        roll_number=str(req.student_id), 
        book_id=req.book_id, 
        loan_days=req.loan_days
    )
    
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"message": "Book borrowed successfully", "due_date": result}

@app.get("/api/students/{roll_number}/loans")
def get_student_loans(roll_number: str):
    """Get active borrowed books, due dates, and fines for a student."""
    from libfind import db
    
    # db.active_loans already fetches the title, due_date, and renewals
    loans = db.active_loans(roll_number)
    
    # Let's add the fine calculation for each loan
    from datetime import datetime
    for loan in loans:
        due = datetime.fromisoformat(str(loan["due_date"]))
        now = datetime.now()
        if now > due:
            days_late = (now - due).days
            loan["days_late"] = days_late
            loan["fine"] = days_late * 5 # ₹5 per day
        else:
            loan["days_late"] = 0
            loan["fine"] = 0
            
    return loans


class BorrowRequestAPI(BaseModel):
    student_id: int
    book_id: int

@app.post("/api/borrow")
def borrow_book_api(req: BorrowRequestAPI):
    from contextlib import closing
    from libfind import db

    try:
        with closing(db.get_connection()) as conn:
            # Fetch the student by ID
            student = conn.execute(
                "SELECT name, email, roll_number FROM students WHERE id = ?", 
                (req.student_id,)
            ).fetchone()
            
            if not student:
                raise HTTPException(status_code=404, detail="Student not found in DB")

            # Call the borrow function
            ok, result = db.borrow_book(
                student_name=student["name"],
                student_email=student["email"],
                roll_number=student["roll_number"],
                book_id=req.book_id,
                loan_days=14
            )
            
            if not ok:
                raise HTTPException(status_code=400, detail=result)
                
        return {"message": "Book borrowed successfully", "due_date": result}
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    

# --- NEW: Define the ReserveRequestAPI class here ---
class ReserveRequestAPI(BaseModel):
    student_id: int
    book_id: int

@app.post("/api/reserve")
def reserve_book_api(req: ReserveRequestAPI):
    """Reserve a checked-out book."""
    from libfind import db
    ok, msg = db.reserve_book(req.student_id, req.book_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

class AdminLogin(BaseModel):
    username: str
    password: str

@app.post("/api/admin/login")
def admin_login(req: AdminLogin):
    """Verify admin credentials from Streamlit secrets."""
    import streamlit as st
    try:
        # Load from .streamlit/secrets.toml or default
        expected_user = str(st.secrets.get("ADMIN_USERNAME", "admin")).strip()
        expected_pass = str(st.secrets.get("ADMIN_PASSWORD", "admin123")).strip()
    except Exception:
        expected_user, expected_pass = "admin", "admin123"

    if req.username == expected_user and req.password == expected_pass:
        return {"message": "Admin login successful", "token": "admin-logged-in"}
    else:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

@app.get("/api/admin/stats")
def get_admin_stats():
    """Fetch dashboard stats for the Admin."""
    from libfind import db
    return db.get_admin_dashboard_stats()

@app.get("/api/students/{roll_number}/dashboard")
def get_student_dashboard(roll_number: str):
    """Fetch a student's profile, fines, active loans, and reservations."""
    from contextlib import closing
    from libfind import db
    from datetime import datetime

    with closing(db.get_connection()) as conn:
        # 1. Get Student Info
        student = conn.execute("SELECT id, name, email, roll_number FROM students WHERE roll_number = ?", (roll_number,)).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student_id = student["id"]

        # 2. Get Active Loans
        loans = db.active_loans(roll_number)
        
        # 3. Get Pending Reservations
        reservations = conn.execute("""
            SELECT r.id, bk.title, r.reserve_date 
            FROM reservations r
            JOIN books bk ON r.book_id = bk.id
            WHERE r.student_id = ? AND r.status = 'pending'
        """, (student_id,)).fetchall()

        # 4. Get Total Unpaid Fines
        fines = conn.execute("""
            SELECT COALESCE(SUM(fine_amount), 0) as total_fines 
            FROM borrows 
            WHERE student_id = ? AND fine_paid = 0
        """, (student_id,)).fetchone()

    return {
        "student": dict(student),
        "active_loans": [dict(l) for l in loans],
        "reservations": [dict(r) for r in reservations],
        "total_fines": fines["total_fines"]
    }
@app.get("/api/students/lookup/{roll_number}")
def lookup_student(roll_number: str):
    """Look up a student by roll number for the Quick Scan page."""
    from libfind import db
    student = db.get_student_by_roll(roll_number)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@app.get("/api/debug")
def debug_db():
    import traceback
    from libfind import db
    try:
        # Try to connect directly to Turso
        conn = db.get_connection()
        # Run a simple query
        res = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        return {"status": "success", "books_count": res}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

class AdminLogin(BaseModel):
    username: str
    password: str

@app.post("/api/admin/login")
def admin_login(req: AdminLogin):
    import os
    # Check environment variables (Render) or fallback
    expected_user = os.environ.get("ADMIN_USERNAME", "admin")
    expected_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    if req.username == expected_user and req.password == expected_pass:
        return {"token": "admin-authenticated"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/admin/stats")
def admin_stats():
    from libfind import db
    return db.get_admin_dashboard_stats()

@app.get("/api/admin/reminders")
def get_reminders():
    from libfind import db
    # Get students who are overdue or due in 2 days
    return db.get_students_for_reminder(days_threshold=2)

@app.post("/api/admin/send-emails")
def send_emails():
    # Mocking the email send for the API. 
    # In a real app, you would loop through reminders and call emailer.send_reminder_email
    return {"message": "Emails sent successfully to all overdue students!"}