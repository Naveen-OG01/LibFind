"""Quick Barcode / QR Scanner UI for Librarians."""
import streamlit as st
from datetime import datetime, timedelta
from libfind import db

def render():
    st.title("📷 Quick Scan (Checkout / Return)")
    st.caption("Use a USB barcode scanner or type the ID manually and press Enter.")

    student = st.session_state.get("student")

    # ---- STUDENT SCAN SECTION ----
    st.subheader("1️⃣ Scan Student ID")
    
    # We use a form so pressing 'Enter' in the text box doesn't reload the whole page
    with st.form("scan_student_form"):
        roll_input = st.text_input("Scan or type Student Roll Number", key="scan_roll")
        find_student = st.form_submit_button("Find Student")

    if find_student or "scan_active_student" in st.session_state:
        # If they typed a new roll number, look it up
        if find_student:
            if not roll_input.strip():
                st.error("Please type or scan a roll number.")
                if "scan_active_student" in st.session_state:
                    del st.session_state["scan_active_student"]
            else:
                found = db.get_student_by_roll(roll_input)
                if found:
                    st.session_state["scan_active_student"] = found
                    st.rerun()
                else:
                    st.error(f"No student found with roll number '{roll_input}'")
                    if "scan_active_student" in st.session_state:
                        del st.session_state["scan_active_student"]

        # If a student is found, show their details
        if "scan_active_student" in st.session_state:
            active_student = st.session_state["scan_active_student"]
            st.success(f"👤 **{active_student['name']}** ({active_student['roll_number']})")
            
            if st.button("Clear Student"):
                del st.session_state["scan_active_student"]
                st.rerun()

            st.divider()

            # ---- BOOK SCAN SECTION ----
            st.subheader("2️⃣ Scan Book ID")
            
            with st.form("scan_book_form"):
                book_id_str = st.text_input("Scan or type Book ID (e.g., 1, 2, 3)")
                checkout_btn = st.form_submit_button("⚡ Process Checkout", type="primary")

            if checkout_btn:
                if not book_id_str.strip().isdigit():
                    st.error("Please enter a valid numeric Book ID.")
                else:
                    book_id = int(book_id_str)
                    # Call the borrow_book function we already built!
                    ok, result = db.borrow_book(
                        active_student["name"], 
                        active_student["email"], 
                        active_student["roll_number"], 
                        book_id, 
                        14 # Default 14 days
                    )
                    if ok:
                        st.success(f"✅ Success! Book ID {book_id} checked out to {active_student['name']}. Due: {str(result)[:10]}")
                        st.balloons()
                    else:
                        st.error(f"Checkout Failed: {result}")