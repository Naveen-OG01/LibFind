import csv
import io
import os
import secrets
import time
from contextlib import closing
from datetime import datetime
from typing import Optional

import streamlit as st
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from libfind import analytics, auth, db, recommend, search


app = FastAPI(title="LibFind API", description="Backend API for the LibFind Library System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
_sessions = {}
_SESSION_TTL_SECONDS = 8 * 60 * 60
_MAX_CSV_BYTES = 5 * 1024 * 1024


class LoginRequest(BaseModel):
    roll_number: str
    password: str


class RegisterRequest(LoginRequest):
    name: str
    email: str


class AdminLogin(BaseModel):
    username: str
    password: str


class BorrowRequest(BaseModel):
    student_id: int
    book_id: int
    loan_days: int = Field(default=14, ge=1, le=30)


class ReserveRequest(BaseModel):
    student_id: int
    book_id: int


class BookCreate(BaseModel):
    title: str = Field(min_length=1)
    author: str = Field(min_length=1)
    isbn: Optional[str] = None
    category: str = "General"
    publisher: str = ""
    publication_year: Optional[int] = Field(default=None, ge=0, le=2100)
    total_copies: int = Field(default=1, ge=1, le=10000)
    available_copies: Optional[int] = Field(default=None, ge=0, le=10000)
    shelf: str = ""
    rack: str = ""
    description: str = ""


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PasswordReset(BaseModel):
    password: str = Field(min_length=6)


class ReturnRequest(BaseModel):
    fine_paid: bool = False


def _issue_session(role, **details):
    now = time.monotonic()
    expired = [token for token, session in _sessions.items() if session["expires_at"] <= now]
    for token in expired:
        del _sessions[token]

    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "role": role,
        "expires_at": now + _SESSION_TTL_SECONDS,
        **details,
    }
    return token


def _current_session(authorization: Optional[str] = Header(default=None)):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="A valid bearer token is required.")

    session = _sessions.get(token)
    if not session or session["expires_at"] <= time.monotonic():
        _sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return session


def _require_admin(session=Depends(_current_session)):
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Librarian access is required.")
    return session


def _require_student(session=Depends(_current_session)):
    if session["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access is required.")
    return session


def _expected_admin_credentials():
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")
    if not username or not password:
        try:
            username = username or st.secrets.get("ADMIN_USERNAME")
            password = password or st.secrets.get("ADMIN_PASSWORD")
        except Exception:
            pass
    if not username or not password:
        raise HTTPException(
            status_code=503,
            detail="Librarian login is not configured on the API.",
        )
    return str(username).strip(), str(password).strip()


def _student_by_id(student_id):
    with closing(db.get_connection()) as conn:
        row = conn.execute(
            "SELECT id, name, email, roll_number FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
    return dict(row) if row else None


def _student_dashboard(roll_number):
    with closing(db.get_connection()) as conn:
        student = conn.execute(
            "SELECT id, name, email, roll_number FROM students WHERE roll_number = ?",
            (roll_number.strip().upper(),),
        ).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")

        student_data = dict(student)
        reservations = conn.execute(
            """
            SELECT r.id, bk.title, r.reserve_date
            FROM reservations r
            JOIN books bk ON bk.id = r.book_id
            WHERE r.student_id = ? AND r.status = 'pending'
            ORDER BY r.reserve_date
            """,
            (student_data["id"],),
        ).fetchall()
        fines = conn.execute(
            """
            SELECT COALESCE(SUM(fine_amount), 0) AS total_fines
            FROM borrows
            WHERE student_id = ? AND fine_paid = 0
            """,
            (student_data["id"],),
        ).fetchone()

    loans = db.active_loans(student_data["roll_number"])
    for loan in loans:
        days_late, fine = db.compute_fine(loan.get("due_date"))
        loan["days_late"] = days_late
        loan["fine"] = fine
    return {
        "student": student_data,
        "active_loans": loans,
        "reservations": [dict(row) for row in reservations],
        "total_fines": fines["total_fines"],
    }


def _csv_rows(content, required_fields):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be encoded as UTF-8.") from exc

    reader = csv.DictReader(io.StringIO(text))
    fields = {(name or "").strip().lower() for name in (reader.fieldnames or [])}
    if not set(required_fields).issubset(fields):
        expected = ", ".join(required_fields)
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include these columns: {expected}.",
        )
    rows = []
    for raw in reader:
        rows.append(
            {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in raw.items()
                if key is not None
            }
        )
    return rows


def _book_values(book):
    return {
        "title": book.title.strip(),
        "author": book.author.strip(),
        "isbn": book.isbn,
        "category_name": book.category.strip() or "General",
        "publisher": book.publisher,
        "publication_year": book.publication_year,
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
        "shelf": book.shelf,
        "rack": book.rack,
        "description": book.description,
    }


@router.get("/")
def read_root():
    return {"message": "Welcome to the LibFind API!"}


@router.get("/api/books")
def get_books():
    return db.get_all_books()


@router.get("/api/categories")
def get_categories():
    return db.category_names()


@router.get("/api/books/search")
def search_books(
    q: str = "",
    field: str = "all",
    category: Optional[str] = None,
    availability: str = "any",
    year: Optional[int] = None,
):
    books = search.search_books(q, field=field, category=category)
    if availability == "available":
        books = [book for book in books if int(book.get("available_copies") or 0) > 0]
    elif availability == "checked_out":
        books = [book for book in books if int(book.get("available_copies") or 0) == 0]
    if year:
        books = [book for book in books if book.get("publication_year") == year]
    return books


@router.get("/api/books/suggestions")
def book_suggestions(
    q: str,
    category: Optional[str] = None,
    availability: str = "any",
    year: Optional[int] = None,
):
    books = search.fuzzy_title_suggestions(q, category=category)
    if availability == "available":
        books = [book for book in books if int(book.get("available_copies") or 0) > 0]
    elif availability == "checked_out":
        books = [book for book in books if int(book.get("available_copies") or 0) == 0]
    if year:
        books = [book for book in books if book.get("publication_year") == year]
    return books


@router.get("/api/books/{book_id}/recommendations")
def get_recommendations(book_id: int):
    if not db.get_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found.")
    return recommend.similar_books(book_id)


@router.post("/api/login")
def login(req: LoginRequest):
    ok, result = auth.login_student(req.roll_number, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=result)
    token = _issue_session(
        "student",
        student_id=result["id"],
        roll_number=result["roll_number"],
    )
    return {"message": "Login successful", "student": result, "token": token}


@router.post("/api/register")
def register(req: RegisterRequest):
    ok, message = auth.register_student(
        req.name,
        req.email,
        req.roll_number,
        req.password,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    ok, student = auth.login_student(req.roll_number, req.password)
    if not ok:
        raise HTTPException(status_code=500, detail="Account created but automatic sign-in failed.")
    token = _issue_session(
        "student",
        student_id=student["id"],
        roll_number=student["roll_number"],
    )
    return {"message": message, "student": student, "token": token}


@router.get("/api/students/{roll_number}/loans")
def get_student_loans(roll_number: str, session=Depends(_require_student)):
    if session["roll_number"].upper() != roll_number.strip().upper():
        raise HTTPException(status_code=403, detail="You can only view your own loans.")
    loans = db.active_loans(roll_number)
    for loan in loans:
        days_late, fine = db.compute_fine(loan.get("due_date"))
        loan["days_late"] = days_late
        loan["fine"] = fine
    return loans


@router.get("/api/students/{roll_number}/dashboard")
def get_student_dashboard(roll_number: str, session=Depends(_require_student)):
    if session["roll_number"].upper() != roll_number.strip().upper():
        raise HTTPException(status_code=403, detail="You can only view your own account.")
    return _student_dashboard(roll_number)


@router.post("/api/borrow")
def borrow_book(req: BorrowRequest, session=Depends(_current_session)):
    student = _student_by_id(req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    if session["role"] == "student" and session["student_id"] != req.student_id:
        raise HTTPException(status_code=403, detail="You can only borrow books for your account.")
    ok, result = db.borrow_book(
        student_name=student["name"],
        student_email=student["email"],
        roll_number=student["roll_number"],
        book_id=req.book_id,
        loan_days=req.loan_days,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"message": "Book borrowed successfully", "due_date": result}


@router.post("/api/reserve")
def reserve_book(req: ReserveRequest, session=Depends(_require_student)):
    if session["student_id"] != req.student_id:
        raise HTTPException(status_code=403, detail="You can only reserve books for your account.")
    book = db.get_book(req.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found.")
    if int(book["available_copies"]) > 0:
        raise HTTPException(status_code=400, detail="This book is currently available to borrow.")
    ok, message = db.reserve_book(req.student_id, req.book_id)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/api/admin/login")
def admin_login(req: AdminLogin):
    expected_user, expected_pass = _expected_admin_credentials()
    if req.username.strip() != expected_user or req.password.strip() != expected_pass:
        raise HTTPException(status_code=401, detail="Invalid librarian credentials.")
    return {"token": _issue_session("admin")}


@router.get("/api/students/lookup/{roll_number}")
def lookup_student(roll_number: str, _=Depends(_require_admin)):
    student = db.get_student_by_roll(roll_number)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


@router.get("/api/debug")
def debug_db():
    with closing(db.get_connection()) as conn:
        count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    return {"status": "success", "books_count": count}


@router.get("/api/admin/stats")
def admin_stats(_=Depends(_require_admin)):
    return db.get_admin_dashboard_stats()


@router.get("/api/admin/reminders")
def get_reminders(days: int = 2, _=Depends(_require_admin)):
    if not 0 <= days <= 30:
        raise HTTPException(status_code=400, detail="Days must be between 0 and 30.")
    return db.get_students_for_reminder(days_threshold=days)


@router.post("/api/admin/send-emails")
def send_emails(days: int = 2, _=Depends(_require_admin)):
    from libfind import emailer

    if not 0 <= days <= 30:
        raise HTTPException(status_code=400, detail="Days must be between 0 and 30.")
    reminders = db.get_students_for_reminder(days_threshold=days)
    sent = 0
    errors = []
    for reminder in reminders:
        due_date = datetime.fromisoformat(str(reminder["due_date"]))
        ok, message = emailer.send_reminder_email(
            reminder["email"],
            reminder["name"],
            reminder["title"],
            reminder["due_date"],
            due_date < datetime.now(),
        )
        if ok:
            sent += 1
        else:
            errors.append(message)
    return {"sent": sent, "errors": errors, "message": f"Sent {sent} of {len(reminders)} reminders."}


@router.post("/api/admin/bulk-import-books")
async def bulk_import_books(file: UploadFile = File(...), _=Depends(_require_admin)):
    content = await file.read(_MAX_CSV_BYTES + 1)
    if len(content) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV files must be 5 MB or smaller.")
    rows = _csv_rows(content, ("title", "author"))
    added, errors = 0, []
    for index, row in enumerate(rows, start=2):
        if not row.get("title"):
            errors.append(f"Row {index}: title is required.")
            continue
        try:
            db.add_book(
                title=row["title"],
                author=row["author"],
                isbn=row.get("isbn") or None,
                category_name=row.get("category") or "General",
                publisher=row.get("publisher") or "",
                publication_year=int(row["year"]) if row.get("year") else None,
                total_copies=int(row.get("total_copies") or 1),
                shelf=row.get("shelf") or "",
                rack=row.get("rack") or "",
            )
            added += 1
        except Exception as exc:
            errors.append(f"Row {index}: {exc}")
    return {"added": added, "errors": errors, "message": f"Successfully imported {added} books."}


@router.post("/api/admin/bulk-import-students")
async def bulk_import_students(file: UploadFile = File(...), _=Depends(_require_admin)):
    content = await file.read(_MAX_CSV_BYTES + 1)
    if len(content) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV files must be 5 MB or smaller.")
    rows = _csv_rows(content, ("name", "email", "roll_number"))
    added, errors = db.bulk_import_students(rows)
    return {"added": added, "errors": errors, "message": f"Successfully imported {added} students."}


@router.get("/api/admin/books")
def get_admin_books(_=Depends(_require_admin)):
    return db.get_all_books()


@router.post("/api/admin/books")
def add_admin_book(book: BookCreate, _=Depends(_require_admin)):
    values = _book_values(book)
    available_copies = values.pop("available_copies")
    try:
        db.add_book(
            **values,
            available_copies=(
                book.total_copies
                if available_copies is None
                else available_copies
            ),
        )
        return {"message": "Book added successfully."}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/admin/books/{book_id}")
def update_admin_book(book_id: int, book: BookCreate, _=Depends(_require_admin)):
    current = db.get_book(book_id)
    if not current:
        raise HTTPException(status_code=404, detail="Book not found.")

    values = _book_values(book)
    requested_available = values.pop("available_copies")
    if requested_available is None:
        currently_borrowed = int(current["total_copies"]) - int(current["available_copies"])
        requested_available = max(0, book.total_copies - currently_borrowed)
    values["available_copies"] = min(requested_available, book.total_copies)
    try:
        db.update_book(book_id, **values)
        return {"message": "Book updated successfully."}
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/admin/books/{book_id}/cover")
async def upload_admin_book_cover(
    book_id: int,
    file: UploadFile = File(...),
    _=Depends(_require_admin),
):
    if not db.get_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found.")
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Cover image must be PNG or JPEG.")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Cover images must be 5 MB or smaller.")
    valid_image = (
        file.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")
    ) or (
        file.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")
    )
    if not valid_image:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PNG or JPEG image.")

    from libfind.cloudinary_config import upload_cover

    cover_url = upload_cover(content, book_id)
    if not cover_url:
        raise HTTPException(status_code=502, detail="Cover upload failed. Check Cloudinary configuration.")
    db.update_book_cover(book_id, cover_url)
    return {"message": "Book cover updated.", "cover_image": cover_url}


@router.delete("/api/admin/books/{book_id}")
def delete_admin_book(book_id: int, _=Depends(_require_admin)):
    if not db.get_book(book_id):
        raise HTTPException(status_code=404, detail="Book not found.")
    db.delete_book(book_id)
    if db.get_book(book_id):
        raise HTTPException(status_code=400, detail="Could not delete the book.")
    return {"message": "Book deleted successfully."}


@router.get("/api/admin/categories")
def get_admin_categories(_=Depends(_require_admin)):
    return db.list_categories()


@router.post("/api/admin/categories")
def add_admin_category(category: CategoryCreate, _=Depends(_require_admin)):
    name = category.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required.")
    db.add_category(name)
    return {"message": f"Category '{name}' added.", "categories": db.list_categories()}


@router.delete("/api/admin/categories/{name}")
def delete_admin_category(name: str, _=Depends(_require_admin)):
    try:
        db.delete_category_by_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": f"Category '{name}' deleted."}


@router.get("/api/admin/students")
def get_admin_students(_=Depends(_require_admin)):
    return db.list_students()


@router.delete("/api/admin/students/{student_id}")
def delete_admin_student(student_id: int, _=Depends(_require_admin)):
    ok, message = db.delete_student(student_id)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/api/admin/students/{roll_number}/reset-password")
def reset_student_password(
    roll_number: str,
    request: PasswordReset,
    _=Depends(_require_admin),
):
    ok, message = auth.admin_reset_password(roll_number, request.password)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.get("/api/admin/reservations")
def get_admin_reservations(_=Depends(_require_admin)):
    return db.get_reservations()


@router.get("/api/admin/loans")
def get_admin_loans(_=Depends(_require_admin)):
    loans = db.active_loans()
    for loan in loans:
        days_late, fine = db.compute_fine(loan.get("due_date"))
        loan["days_late"] = days_late
        loan["fine"] = fine
    return loans


@router.post("/api/admin/loans/{borrow_id}/return")
def return_admin_loan(borrow_id: int, request: ReturnRequest, _=Depends(_require_admin)):
    ok, message = db.return_book(borrow_id, fine_paid=request.fine_paid)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/api/admin/loans/{borrow_id}/renew")
def renew_admin_loan(borrow_id: int, _=Depends(_require_admin)):
    ok, message = db.renew_book(borrow_id)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.get("/api/admin/records")
def get_admin_records(_=Depends(_require_admin)):
    return db.borrow_history()


@router.get("/api/admin/activity")
def get_admin_activity(limit: int = 200, _=Depends(_require_admin)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500.")
    return db.get_activity(limit=limit)


@router.get("/api/admin/analytics")
def get_admin_analytics(_=Depends(_require_admin)):
    overdue = db.overdue_summary()
    return {
        "collection": analytics.collection_summary(),
        "categories": analytics.category_stats(),
        "authors": analytics.top_authors(limit=8),
        "most_borrowed": analytics.most_borrowed(limit=10),
        "low_stock": analytics.low_stock(limit=10),
        "overdue": overdue,
        "overdue_fines": sum(item["fine"] for item in overdue),
    }


def _borrow_records_csv():
    rows = db.borrow_history()
    output = io.StringIO()
    fields = (
        "name",
        "roll_number",
        "title",
        "borrow_date",
        "due_date",
        "return_date",
        "status",
        "fine_amount",
        "fine_paid",
    )
    writer = csv.writer(output)
    writer.writerow(fields)
    for row in rows:
        writer.writerow([row.get(field, "") for field in fields])
    return output.getvalue()


@router.get("/api/admin/reports/{report_name}")
def download_admin_report(report_name: str, _=Depends(_require_admin)):
    reports = {
        "inventory": db.export_full_inventory,
        "students": db.export_all_students,
        "fines": db.export_fine_report,
        "borrows": _borrow_records_csv,
    }
    if report_name not in reports:
        raise HTTPException(status_code=404, detail="Unknown report.")
    filename = f"libfind_{report_name}.csv"
    return Response(
        content=reports[report_name](),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app.include_router(router)
