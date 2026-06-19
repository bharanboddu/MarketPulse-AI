"""WSGI entry point for production deployment (Gunicorn)."""
from run import app

if __name__ == "__main__":
    app.run()
