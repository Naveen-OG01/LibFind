"""Library analytics dashboard UI."""
import pandas as pd
import plotly.express as px
import streamlit as st

from libfind import analytics as core
from libfind import db

def render():
    st.title("📊 Library Analytics")
    st.title("📊 Library Analytics")
    st.caption("Live reports from the LibFind catalogue.")
    
    # ---- NEW: UNPAID FINES SUMMARY ----
    from libfind import db as _db
    from contextlib import closing
    
    with closing(_db.get_connection()) as conn:
        unpaid = conn.execute(
            """SELECT SUM(fine_amount) as total, COUNT(*) as count 
               FROM borrows 
               WHERE status = 'returned' AND fine_paid = 0 AND fine_amount > 0"""
        ).fetchone()
        
    if unpaid and unpaid["count"] > 0:
        st.error(f"⚠️ **Pending Fines:** {unpaid['count']} students owe a total of **₹{unpaid['total']}**. Check the 'View Records' tab to collect.")
    else:
        st.success("✅ All previous fines have been collected. No pending payments.")
    st.divider()
    # -----------------------------------
    st.caption("Live reports from the LibFind catalogue.")
    st.subheader("⚠️ Low-availability books")

    summary = core.collection_summary()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Book Titles", summary["total_titles"])
    col2.metric("Total Copies", summary["total_copies"])
    col3.metric("Available Copies", summary["available_copies"])
    col4.metric("Availability", f'{summary["percent_available"]:.1f}%')

    st.subheader("⚠️ Overdue loans & fines")
    overdue = db.overdue_summary()
    if overdue:
        total_fine = sum(o["fine"] for o in overdue)
        c1, c2 = st.columns(2)
        c1.metric("Overdue loans", len(overdue))
        c2.metric("Fines owed", f"₹{total_fine}")

        odf = pd.DataFrame(overdue)
        fig_o = px.bar(
            odf,
            x="fine",
            y="title",
            orientation="h",
            color="days_overdue",
            color_continuous_scale="Reds",
            title="Fines by book",
            labels={"fine": "Fine (₹)", "title": "Book", "days_overdue": "Days late"},
        )
        st.plotly_chart(fig_o, use_container_width=True)
        st.dataframe(
            odf[["name", "roll_number", "title", "due_date", "days_overdue", "fine"]]
            .rename(columns={
                "name": "Student",
                "roll_number": "Roll No",
                "title": "Book",
                "due_date": "Due",
                "days_overdue": "Days late",
                "fine": "Fine (₹)",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No overdue loans — all books are on time. 🎉")

    st.subheader("Category-wise copies")
    cat_data = core.category_stats()

    if cat_data:
        df = pd.DataFrame(cat_data)

        fig = px.bar(
            df,
            x="category_name",
            y=["total_copies", "available_copies"],
            barmode="group",
            title="Total and available copies by category",
            labels={
                "value": "Copies",
                "category_name": "Category",
                "variable": "Type",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No category data available yet.")

    st.subheader("Top authors by copies")
    authors = core.top_authors(limit=8)

    if authors:
        author_df = pd.DataFrame(authors)

        fig2 = px.bar(
            author_df,
            x="author",
            y="copies",
            color="titles",
            title="Top library authors",
            labels={
                "author": "Author",
                "copies": "Copies in library",
                "titles": "Book titles",
            },
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No author data yet.")


    st.subheader("🏆 Most borrowed books")
    borrowed = core.most_borrowed(limit=10)

    if borrowed:
        bdf = pd.DataFrame(borrowed)
        fig3 = px.bar(
            bdf,
            x="times_borrowed",
            y="title",
            orientation="h",
            title="Most borrowed books",
            labels={"times_borrowed": "Times borrowed", "title": "Book"},
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No borrowing activity yet.")
    

    st.subheader("⚠️ Low-availability books")
    low = core.low_stock(limit=10)

    if low:
        low_df = pd.DataFrame(low)
        st.dataframe(
            low_df.rename(
                columns={
                    "title": "Title",
                    "total_copies": "Total Copies",
                    "available_copies": "Available",
                    "category_name": "Category",
                    "shelf": "Shelf",
                    "rack": "Rack",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("All books are fully available — no low-stock items.")
