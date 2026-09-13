import streamlit as st
import cloudinary
import cloudinary.uploader


def _configure_cloudinary():
    required = ["CLOUD_NAME", "API_KEY", "API_SECRET"]
    missing = [key for key in required if not st.secrets.get(key)]

    if missing:
        st.warning(
            "Cloudinary is not configured. Missing secrets: "
            + ", ".join(missing)
        )
        return False

    cloudinary.config(
        cloud_name=st.secrets["CLOUD_NAME"],
        api_key=st.secrets["API_KEY"],
        api_secret=st.secrets["API_SECRET"],
        secure=True,
    )
    return True


def upload_cover(file_bytes, book_id):
    if not _configure_cloudinary():
        return None
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=f"libfind/covers/book_{book_id}",
            overwrite=True,
            transformation={"width": 300, "height": 450, "crop": "fill"},
        )
        return result["secure_url"]
    except Exception as exc:
        st.error(f"Cover upload failed: {exc}")
        return None
