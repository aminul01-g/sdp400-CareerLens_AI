import json
import os
import sys

# ensure backend package on path
basedir = os.path.dirname(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app
from extensions import db

with app.app_context():
    print('Creating tables (if not present)')
    db.create_all()

    from models import Event, Profile, User

    def ensure_user(email, name, password, role='user'):
        u = User.query.filter_by(email=email).first()
        if u:
            print(f'User already exists: {email} (id={u.id})')
            return u
        u = User(name=name, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        print(f'Created user: {email} (id={u.id})')
        # create empty profile
        p = Profile(user_id=u.id, headline='Sample headline', skills='python,sql,ml')
        db.session.add(p)
        db.session.commit()
        print(f'Created profile for user id={u.id}')
        return u

    # create admin and a test user
    admin = ensure_user('admin@example.com', 'Admin User', 'AdminPass123', role='admin')
    test = ensure_user('testuser@example.com', 'Test User', 'TestPass123')

    # add a sample event
    ev = Event(user_id=test.id, name='seed_started', metadata_json=json.dumps({'note': 'seed script ran'}))
    db.session.add(ev)
    db.session.commit()
    print(f'Created event id={ev.id} for user id={test.id}')

    print('\nSummary counts:')
    print('Users:', User.query.count())
    print('Profiles:', Profile.query.count())
    print('Events:', Event.query.count())
