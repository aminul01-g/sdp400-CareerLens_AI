import os
import sys

# ensure backend package root is on sys.path
basedir = os.path.dirname(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app

with app.app_context():
    from models import Feedback
    fbs = Feedback.query.order_by(Feedback.created_at.desc()).limit(20).all()
    for f in fbs:
        print(f.to_dict())
