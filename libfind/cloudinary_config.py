import streamlit as st
import cloudinary
import cloudinary.uploader

cfg = st.secrets
cloudinary.config(
    cloud_name=cfg["CLOUD_NAME"],
    api_key=cfg["API_KEY"],
    api_secret=cfg["API_SECRET"],
)


def upload_cover(file_bytes, book_id):
    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=f"libfind/covers/book_{book_id}",
        overwrite=True,
        transformation={"width": 300, "height": 450, "crop": "fill"},
    )
    return result["secure_url"]
