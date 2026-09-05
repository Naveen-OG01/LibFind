"""Library analytics dashboard UI."""
import pandas as pd
import plotly.express as px
import streamlit as st

from libfind import analytics as core


def render():
    st.title("📊 Library Analytics")
    st.caption("Live reports from the LibFind catalogue.")

    summary = core.collection_summary()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Book Titles", summary["total_titles"])
    col2.metric("Total Copies", summary["total_copies"])
    col3.metric("Available Copies", summary["available_copies"])
    col4.metric("Availability", f'{summary["percent_available"]:.1f}%')

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
