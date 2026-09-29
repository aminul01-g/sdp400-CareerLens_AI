import os
import logging
from flask import Flask
from dotenv import load_dotenv
from extensions import db, jwt, admin, scheduler
from flask_cors import CORS
from auth import auth_bp
from guidance import guidance_bp
from admin import init_admin
from tasks import start_scheduler

load_dotenv()

def create_app():
    app = Flask(__name__)
    # ensure logger prints INFO level messages
    app.logger.setLevel(logging.INFO)
    CORS(app)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///./pathfinder.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './uploads')

    db.init_app(app)
    jwt.init_app(app)
    admin.init_app(app)  # minimal; models registered in admin.py

    # Log DB location and upload folder so developers know where data is stored
    try:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI')
        if uri and uri.startswith('sqlite'):
            db_path = uri.split('sqlite:///')[-1]
            db_path = os.path.abspath(db_path)
            app.logger.info(f"SQLALCHEMY_DATABASE_URI={uri} -> {db_path}; exists={os.path.exists(db_path)}")
        else:
            app.logger.info(f"SQLALCHEMY_DATABASE_URI={uri}")
    except Exception:
        app.logger.exception('Error while logging DB path')
    app.logger.info(f"UPLOAD_FOLDER={os.path.abspath(app.config.get('UPLOAD_FOLDER'))}")

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(guidance_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()
        init_admin(app)

    start_scheduler(app)

    @app.route('/')
    def index():
        return {'status': 'ok', 'app': 'Pathfinder AI Guide - Backend'}

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
