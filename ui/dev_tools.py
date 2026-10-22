"""⚠️ DEV ONLY — utilities for testing. Remove before going live."""
import streamlit as st
from datetime import datetime, timedelta
from contextlib import closing

from libfind import db, seed


def render():
    st.title("🛠 Dev Tools")
    st.warning("⚠️ Development only — do not expose in production.")

    st.subheader("Database Status")
    try:
        st.write(f"Books in DB: {db.count_books()}")
        st.write(f"Categories: {len(db.list_categories())}")
    except Exception as e:
        st.error(f"DB read failed: {e}")

    st.divider()

    st.subheader("🔥 Force Overdue Book")
    st.caption("This makes the most recent borrowed book overdue by 5 days so you can test the fine system.")
    if st.button("Make latest borrow overdue"):
        with closing(db.get_connection()) as conn:
            row = conn.execute("SELECT id FROM borrows WHERE status = 'borrowed' ORDER BY id DESC LIMIT 1").fetchone()
            if row:
                new_due = (datetime.now() - timedelta(days=5)).isoformat()
                conn.execute("UPDATE borrows SET due_date = ? WHERE id = ?", (new_due, row["id"] if hasattr(row, "keys") else row[0]))
                conn.commit()
                st.success("✅ Book is now overdue by 5 days! Go to Return/Renew tab to see the fine.")
            else:
                st.error("No active borrowed books found.")

    st.divider()

    st.subheader("Full DB Reset")
    confirm = st.text_input("Type RESET to confirm")
    if st.button("🔥 Nuke + Reseed", type="primary"):
        if confirm.strip().upper() != "RESET":
            st.error("Type RESET exactly to confirm.")
            return

        db_path = db.DB_PATH
        try:
            if db_path.exists():
                db_path.unlink()
            db.init_db()
            seed.seed_if_empty()
            st.success(f"✅ Fresh DB created. Books: {db.count_books()}")
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")