import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Set the SECRET_KEY environment variable in any real deployment.
    # The fallback below is for local development ONLY and must never be used in production.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-insecure-secret-key"

    # SQLite Database
    DATABASE_PATH = os.path.join(BASE_DIR, "inventory.db")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_PATH
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pagination
    ITEMS_PER_PAGE = 12

    # Display settings
    DISPLAY_TIMEZONE = os.environ.get("DISPLAY_TIMEZONE") or "UTC"

    # Uploads
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ITEM_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    AVATAR_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "avatars")
