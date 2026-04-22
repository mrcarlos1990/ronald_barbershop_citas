import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    BASE_DIR = BASE_DIR
    INSTANCE_DIR = BASE_DIR / "instance"
    TEMPLATES_DIR = BASE_DIR / "templates"
    STATIC_DIR = BASE_DIR / "static"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{(INSTANCE_DIR / 'ronald_barbershop.db').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "ronald-barbershop-dev-key")
    JSON_SORT_KEYS = False
