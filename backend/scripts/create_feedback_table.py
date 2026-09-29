import os, sys
# ensure backend package root is on sys.path
basedir = os.path.dirname(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app
from extensions import db

with app.app_context():
    db.create_all()
    try:
        from models import Feedback
        print('Feedback count:', Feedback.query.count())
    except Exception as e:
        print('Error querying Feedback:', e)
