"""Admin / library catalogue management UI."""
import csv
import io

import streamlit as st

from libfind import db
from libfind.cloudinary_config import upload_cover


def render():
    if st.session_state.get("admin_logged_in", False):
        _admin_screen()
    else:
        _login_screen()


def _login_screen():
    st.title("🔐 Admin Login")
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
    if submitted:
        try:
            expected_user = str(st.secrets.get("ADMIN_USERNAME", "admin")).strip()
            expected_pass = str(st.secrets.get("ADMIN_PASSWORD", "admin123")).strip()
        except Exception:
            expected_user, expected_pass = "admin", "admin123"

        if username.strip() == expected_user and password.strip() == expected_pass:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")


def _admin_screen():
    st.title("🛠 Admin / Library Interface")
    if st.sidebar.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

    # Check if dashboard sent us to a specific tab
    if "admin_tab" not in st.session_state:
        st.session_state.admin_tab = "➕ Add Book"

    # If URL params exist, update the session state
    if "tab" in st.query_params:
        tab_map = {
            "add": "➕ Add Book",
            "edit": "✏️ Edit / Delete Book",
            "cat": "🏷️ Categories",
            "bulk": "📄 Bulk Import",
            "students": "👥 Students",
            "bulk_students": "🎓 Bulk Students",
            "notify": "✉️ Notifications",
            "log": "📋 Activity Log"
        }
        target = st.query_params["tab"]
        if target in tab_map:
            st.session_state.admin_tab = tab_map[target]
        
        # Clean up the URL immediately
        del st.query_params["tab"] 

    tabs = [
        "➕ Add Book",
        "✏️ Edit / Delete Book",
        "🏷️ Categories",
        "📄 Bulk Import",
        "👥 Students",
        "🎓 Bulk Students",
        "✉️ Notifications",
        "📋 Activity Log"
    ]
    
    # Put the radio in the sidebar so it doesn't squish
    st.sidebar.divider()
    active_tab = st.sidebar.radio("Admin Menu", tabs, key="admin_tab")

    if active_tab == "➕ Add Book":
        _add_book_tab()
    elif active_tab == "✏️ Edit / Delete Book":
        _edit_delete_book_tab()
    elif active_tab == "🏷️ Categories":
        _categories_tab()
    elif active_tab == "📄 Bulk Import":
        _bulk_import_tab()
    elif active_tab == "👥 Students":
        _students_tab()
    elif active_tab == "🎓 Bulk Students":
        _bulk_students_tab()
    elif active_tab == "✉️ Notifications":
        _notifications_tab()
    elif active_tab == "📋 Activity Log":
        _activity_tab()

def _add_book_tab():
    categories = db.category_names()
    with st.form("add_book_form"):
        st.subheader("Add a new book to the catalogue")
        col1, col2 = st.columns(2)
        title = col1.text_input("Title *")
        author = col2.text_input("Author *")
        col3, col4 = st.columns(2)
        isbn = col3.text_input("ISBN")
        category = col4.text_input("Category", placeholder="e.g. Computer Science")
        col5, col6 = st.columns(2)
        publisher = col5.text_input("Publisher")
        year = col6.number_input("Publication year", 0, 2100, 2024, 1)
        col7, col8 = st.columns(2)
        total_copies = col7.number_input("Total copies", 1, 10000, 1, 1)
        available_copies = col8.number_input("Available copies", 0, 10000, 1, 1)
        col9, col10 = st.columns(2)
        shelf = col9.text_input("Shelf", placeholder="CS-1")
        rack = col10.text_input("Rack", placeholder="R2")
        submitted = st.form_submit_button("Add book", type="primary", use_container_width=True)

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Title and author are required.")
        else:
            try:
                db.add_book(
                    title=title, author=author, isbn=isbn.strip() or None,
                    category_name=category, publisher=publisher,
                    publication_year=year or None,
                    total_copies=total_copies,
                    available_copies=min(available_copies, total_copies),
                    shelf=shelf, rack=rack,
                )
                st.success(f"Book '{title.strip()}' added.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add book: {exc}")


def _edit_delete_book_tab():
    books = db.get_all_books()
    if not books:
        st.info("No books in the catalogue yet.")
        return

    options = {f"#{b['id']} — {b['title']} ({b['author']})": b["id"] for b in books}
    book_id = options[st.selectbox("Select a book", list(options.keys()))]
    book = db.get_book(book_id)
    if not book:
        st.warning("Book not found.")
        return

    st.subheader("📚 Book Cover")
    if book.get("cover_image"):
        st.image(book["cover_image"], width=150, caption="Current cover")
    else:
        st.caption("📚 No cover available")

    uploaded_cover = st.file_uploader("Upload new cover image", type=["png", "jpg", "jpeg"], key=f"cover_upload_{book_id}")

    categories = db.category_names()
    default_cat_idx = (categories.index(book["category_name"]) if book["category_name"] in categories else 0)

    with st.form("edit_book_form"):
        st.subheader("Update book details")
        col1, col2 = st.columns(2)
        title = col1.text_input("Title *", value=book["title"])
        author = col2.text_input("Author *", value=book["author"])
        col3, col4 = st.columns(2)
        isbn = col3.text_input("ISBN", value=book["isbn"] or "")
        category = col4.selectbox("Category", categories, index=default_cat_idx)
        col5, col6 = st.columns(2)
        publisher = col5.text_input("Publisher", value=book["publisher"] or "")
        year = col6.number_input("Publication year", 0, 2100, int(book["publication_year"] or 2024), 1)
        col7, col8 = st.columns(2)
        total_copies = col7.number_input("Total copies", 1, 10000, int(book["total_copies"]), 1)
        available_copies = col8.number_input("Available copies", 0, 10000, int(book["available_copies"]), 1)
        col9, col10 = st.columns(2)
        shelf = col9.text_input("Shelf", value=book["shelf"] or "")
        rack = col10.text_input("Rack", value=book["rack"] or "")
        submitted = st.form_submit_button("Save changes", type="primary", use_container_width=True)

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Title and author are required.")
        elif available_copies > total_copies:
            st.error("Available copies cannot exceed total copies.")
        else:
            try:
                if uploaded_cover:
                    cover_url = upload_cover(uploaded_cover.read(), book_id)
                    if cover_url:
                        db.update_book_cover(book_id, cover_url)
                db.update_book(
                    book_id, title=title, author=author, isbn=isbn,
                    category_name=category, publisher=publisher,
                    publication_year=year or None,
                    total_copies=total_copies,
                    available_copies=available_copies,
                    shelf=shelf, rack=rack,
                )
                st.success("Book updated!")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not update book: {exc}")

    st.divider()
    if st.button("🗑 Delete selected book", use_container_width=True):
        db.delete_book(book_id)
        st.success("Book deleted.")
        st.rerun()


def _categories_tab():
    st.caption("A category with books cannot be deleted.")
    with st.form("add_category_form"):
        col1, col2 = st.columns([3, 1])
        name = col1.text_input("New category name")
        add_clicked = col2.form_submit_button("Add", use_container_width=True)
    if add_clicked and name.strip():
        db.add_category(name)
        st.success(f"Category '{name.strip()}' added.")
        st.rerun()

    st.divider()
    cats = db.list_categories()
    if cats:
        st.dataframe([{"Category": c["name"], "Books": c["book_count"]} for c in cats], use_container_width=True, hide_index=True)
        empty = [c["name"] for c in cats if c["book_count"] == 0]
        if empty:
            target = st.selectbox("Delete empty category", empty)
            if st.button("Delete"):
                try:
                    db.delete_category_by_name(target)
                    st.success(f"Deleted '{target}'.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def _bulk_import_tab():
    st.subheader("Bulk add books from a CSV file")
    st.caption("Header row required. Columns: title, author, isbn, category, publisher, year, total_copies, shelf, rack (only title and author are mandatory).")
    
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"], key="bulk_csv")
    if uploaded is None:
        return

    try:
        text = uploaded.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError:
        st.error("Could not read the file — save it as UTF-8 CSV and try again.")
        return

    reader = csv.DictReader(io.StringIO(text))
    fields = {(name or "").strip().lower() for name in (reader.fieldnames or [])}
    if not {"title", "author"}.issubset(fields):
        st.error("CSV must contain 'title' and 'author' columns (header row required).")
        return

    if st.button("📥 Import books", type="primary", key="bulk_import_btn"):
        added, errors = 0, []
        for i, raw in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
            if not row.get("title"):
                continue
            try:
                db.add_book(
                    title=row["title"],
                    author=row.get("author", ""),
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
                errors.append(f"row {i}: {exc}")

        st.success(f"✅ Imported {added} book(s).")
        if errors:
            st.warning(f"{len(errors)} row(s) skipped: " + "; ".join(errors[:8]))


def _students_tab():
    st.subheader("👥 Registered Students")
    
    students = db.list_students()
    
    if not students:
        st.info("No students registered yet.")
        return # Stop here if there are no students

    # 1. Show the table
    import pandas as pd
    df = pd.DataFrame(students).rename(columns={
        "id": "ID",
        "name": "Name",
        "email": "Email",
        "roll_number": "Roll No",
        "active_loans": "Active Borrows",
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Total: {len(students)} students")

    # 2. Delete Student Section
    st.divider()
    st.subheader("🗑️ Delete Student")
    st.caption("Note: You cannot delete a student who currently has books borrowed.")
    
    options = {f"{s['name']} ({s['roll_number']})": s["id"] for s in students}
    selected_student = st.selectbox("Select student to delete", list(options.keys()))
    
    if st.button("Delete Student", type="primary"):
        ok, msg = db.delete_student(options[selected_student])
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    # 3. Reset Password Section
    st.divider()
    st.subheader("🔑 Reset Student Password")
    st.caption("Use this if a student forgets their password.")
    
    with st.form("admin_reset_password_form"):
        col1, col2 = st.columns(2)
        roll = col1.text_input("Student Roll Number")
        new_pwd = col2.text_input("New Password (min 6 chars)", type="password")
        
        submitted = st.form_submit_button("Reset Password", type="primary")
        
    if submitted:
        from libfind import auth
        ok, msg = auth.admin_reset_password(roll, new_pwd)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.divider()
    st.subheader("🔖 Active Book Reservations")
    res = db.get_reservations()
    if res:
        import pandas as pd
        rdf = pd.DataFrame(res).rename(columns={
            "id": "ID", "name": "Student", "roll_number": "Roll No", "title": "Book", "reserve_date": "Date"
        })
        st.dataframe(rdf[["Student", "Roll No", "Book", "Date"]], use_container_width=True, hide_index=True)
    else:
        st.info("No active reservations.")

         
def _notifications_tab():
    st.subheader("✉️ Email Notifications")
    st.caption("Send automated reminders to students whose books are due soon or overdue.")
    
    days = st.number_input("Look-ahead days (include books due within X days)", min_value=0, max_value=30, value=2)
    
    if st.button("🔍 Preview Emails", type="secondary"):
        st.session_state["preview_emails"] = db.get_students_for_reminder(days)
    
    emails = st.session_state.get("preview_emails", [])
    
    if not emails:
        st.info("No books are due soon or overdue. All clear! 🎉")
        return
        
    st.write(f"Found **{len(emails)}** books that need attention.")
    
    import pandas as pd
    df = pd.DataFrame(emails)[["name", "email", "title", "due_date"]]
    df["due_date"] = df["due_date"].astype(str).str[:10]
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    if st.button("🚀 Send All Emails", type="primary"):
        from libfind import emailer
        import datetime
        
        success_count = 0
        errors = []
        
        progress_bar = st.progress(0)
        
        for i, row in enumerate(emails):
            due_dt = datetime.datetime.fromisoformat(str(row["due_date"]))
            is_overdue = due_dt < datetime.datetime.now()
            
            ok, msg = emailer.send_reminder_email(
                row["email"], row["name"], row["title"], row["due_date"], is_overdue
            )
            
            if ok:
                success_count += 1
            else:
                errors.append(msg)
                
            progress_bar.progress((i + 1) / len(emails))
            
        if success_count > 0:
            st.success(f"✅ Successfully sent {success_count} emails!")
        
        if errors:
            st.error("Some emails failed to send:")
            for err in errors:
                st.write(f"- {err}")


def _activity_tab():
    st.subheader("📋 Activity Log")
    st.caption("Latest borrow, return and renew events (most recent first).")

    entries = db.get_activity(limit=200)
    if not entries:
        st.info("No activity recorded yet — borrow or return a book first.")
        return

    st.dataframe(
        [{"When": e["created_at"], "Action": e["action"], "Details": e["details"]} for e in entries],
        use_container_width=True,
        hide_index=True,
    )

def _bulk_students_tab():
    st.subheader("🎓 Bulk Import Students")
    st.caption("Upload a CSV file to register multiple students at once.")
    
    st.info("""
    **CSV Format Required:**
    `name`, `email`, `roll_number` (Only these three are mandatory)
    **Note:** The default password for all imported students will be their **Roll Number**.
    """)

    # Sample download
    sample_csv = "name,email,roll_number\nRahul Sharma,rahul@college.edu,21CS001\nPriya Patel,priya@college.edu,21CS002"
    st.download_button(
        label="⬇️ Download Sample CSV",
        data=sample_csv,
        file_name="sample_students.csv",
        mime="text/csv"
    )

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"], key="bulk_students_csv")
    
    if uploaded is None:
        return

    try:
        text = uploaded.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError:
        st.error("Could not read the file — save it as UTF-8 CSV and try again.")
        return

    reader = csv.DictReader(io.StringIO(text))
    fields = {(name or "").strip().lower() for name in (reader.fieldnames or [])}
    
    if not {"name", "email", "roll_number"}.issubset(fields):
        st.error("CSV must contain 'name', 'email', and 'roll_number' columns.")
        return

    if st.button("📥 Import Students", type="primary", key="bulk_import_students_btn"):
        students_to_add = []
        for raw in reader:
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
            if not row.get("roll_number"):
                continue
            students_to_add.append(row)

        with st.spinner(f"Importing {len(students_to_add)} students..."):
            added, errors = db.bulk_import_students(students_to_add)
            
        st.success(f"✅ Successfully imported {added} students!")
        
        if errors:
            st.warning(f"{len(errors)} student(s) skipped:")
            for err in errors[:10]:
                st.write(f"- {err}")