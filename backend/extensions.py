from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_admin import Admin
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
jwt = JWTManager()
admin = Admin(name='Pathfinder Admin')
scheduler = BackgroundScheduler()
