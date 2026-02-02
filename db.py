from flask_sqlalchemy import SQLAlchemy
import os
from urllib.parse import quote_plus

db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    DB_USER = os.environ.get("DB_USER")
    DB_PASS = quote_plus(os.environ.get("DB_PASS"))
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    DB_NAME = os.environ.get("DB_NAME")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = True

    db.init_app(app)

    with app.app_context():
        db.create_all()