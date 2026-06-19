import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "market-pulse-default-secret-12345")
    
    # Database config: default to SQLite
    base_dir = os.path.abspath(os.path.dirname(__file__))
    sqlite_db_path = os.path.join(base_dir, "marketpulse.db")
    _db_url = os.getenv("DATABASE_URL") or f"sqlite:///{sqlite_db_path}"
    # Render uses postgres:// but SQLAlchemy requires postgresql://
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLite needs timeout for concurrent access; PostgreSQL does not
    if "sqlite" in _db_url:
        SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30.0}}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # AI API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
