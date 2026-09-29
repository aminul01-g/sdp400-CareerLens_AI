import json
import os
import sqlite3
import sys

# Ensure the backend folder is on sys.path so `import app` works when this
# script is executed from anywhere. `scripts` is a subfolder of `backend`.
basedir = os.path.dirname(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

try:
    from app import app
except Exception as e:
    print('ERROR importing app:', e)
    raise

uri = app.config.get('SQLALCHEMY_DATABASE_URI')
print('SQLALCHEMY_DATABASE_URI:', uri)

if uri and uri.startswith('sqlite'):
    # support sqlite:///relative/path or sqlite:////absolute/path
    path = uri.split('sqlite:///')[-1]
    path = os.path.abspath(path)
    print('DB file:', path)
    print('Exists:', os.path.exists(path))
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        print('Tables:', json.dumps(tables))
        for t in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{t}"')
                cnt = cur.fetchone()[0]
            except Exception:
                cnt = 'N/A'
            print(f'Table {t} count: {cnt}')
        if 'user' in tables:
            cur.execute('PRAGMA table_info(user)')
            cols = [r[1] for r in cur.fetchall()]
            cur.execute('SELECT * FROM user LIMIT 5')
            rows = cur.fetchall()
            print('User columns:', json.dumps(cols))
            print('User sample:', json.dumps(rows))
        conn.close()
    except Exception as e:
        print('SQLite error:', e)
else:
    print('DB is not an sqlite file or URI unknown')

# Also try using SQLAlchemy models to show nicer output
with app.app_context():
    try:
        from models import Event, GuidanceSession, Profile, Upload, User
        print('\nSQLAlchemy counts:')
        print('Users:', User.query.count())
        print('Profiles:', Profile.query.count())
        print('Uploads:', Upload.query.count())
        print('GuidanceSessions:', GuidanceSession.query.count())
        print('Events:', Event.query.count())
        sample = User.query.limit(5).all()
        def safe(u):
            try:
                return u.to_dict()
            except Exception:
                return str(u.id)
        print('\nSample users:')
        print(json.dumps([safe(u) for u in sample], indent=2))
    except Exception as e:
        print('SQLAlchemy inspect error:', e)
