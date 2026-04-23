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
