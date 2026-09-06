import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="ii9kpnbm",
    api_key="383859391535822",
    api_secret="UpoFGBLfvvL34rLKvkcZq7-6si0",
)


def upload_cover(file_bytes, book_id):
    """Upload cover image to Cloudinary and return URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=f"libfind/covers/book_{book_id}",
        overwrite=True,
        transformation={"width": 300, "height": 450, "crop": "fill"},
    )
    return result["secure_url"]
