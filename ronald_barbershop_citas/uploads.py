from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import current_app, has_request_context, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadValidationError(ValueError):
    """Raised when a user tries to upload an invalid image."""


def allowed_image_file(filename: str | None) -> bool:
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def build_media_url(value: str | None) -> str | None:
    if not value:
        return None

    if value.startswith(("http://", "https://", "data:", "/static/")):
        return value

    if has_request_context():
        return url_for("static", filename=value)

    return f"/static/{value.lstrip('/')}"


def delete_uploaded_file(relative_path: str | None) -> None:
    if not relative_path or relative_path.startswith(("http://", "https://", "data:")):
        return

    normalized = Path(relative_path.replace("\\", "/"))
    if normalized.parts[:1] != ("uploads",):
        return

    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    candidate = (current_app.static_folder and Path(current_app.static_folder).resolve() / normalized)
    if not candidate:
        return

    try:
        resolved = candidate.resolve()
    except FileNotFoundError:
        return

    if upload_root not in resolved.parents and resolved != upload_root:
        return

    if resolved.exists():
        resolved.unlink()


def _cloudinary_is_configured() -> bool:
    return all(
        current_app.config.get(key)
        for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    )


def _save_to_cloudinary(file_storage: FileStorage, *, tenant_id: int, category: str) -> str | None:
    if current_app.config.get("IMAGE_STORAGE_BACKEND") != "cloudinary" or not _cloudinary_is_configured():
        return None

    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError:
        return None

    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    folder = f"{current_app.config.get('CLOUDINARY_FOLDER', 'ronald_barbershop')}/tenant_{tenant_id}/{category}"
    try:
        result = cloudinary.uploader.upload(file_storage, folder=folder, resource_type="image")
    except Exception:
        file_storage.stream.seek(0)
        return None
    return result.get("secure_url")


def save_image_upload(
    file_storage: FileStorage | None,
    *,
    tenant_id: int,
    category: str,
    current_path: str | None = None,
) -> str | None:
    if file_storage is None or not file_storage.filename:
        return current_path

    if not allowed_image_file(file_storage.filename):
        allowed = ", ".join(sorted(current_app.config["ALLOWED_IMAGE_EXTENSIONS"]))
        raise UploadValidationError(f"Formato de imagen no permitido. Usa: {allowed}.")

    cloudinary_url = _save_to_cloudinary(file_storage, tenant_id=tenant_id, category=category)
    if cloudinary_url:
        if current_path and current_path != cloudinary_url:
            delete_uploaded_file(current_path)
        return cloudinary_url

    original_name = secure_filename(file_storage.filename)
    extension = Path(original_name).suffix.lower()
    stem = Path(original_name).stem or category

    target_folder = Path(current_app.config["UPLOAD_FOLDER"]) / f"tenant_{tenant_id}" / category
    target_folder.mkdir(parents=True, exist_ok=True)

    unique_name = f"{stem}-{uuid4().hex[:10]}{extension}"
    target_path = target_folder / unique_name
    file_storage.save(target_path)

    relative_path = (Path("uploads") / f"tenant_{tenant_id}" / category / unique_name).as_posix()

    if current_path and current_path != relative_path:
        delete_uploaded_file(current_path)

    return relative_path
