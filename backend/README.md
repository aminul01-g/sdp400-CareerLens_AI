Pathfinder AI Guide - Flask Backend (starter)
=============================================

What's included:
- Flask app with SQLAlchemy (SQLite) and JWT auth (flask-jwt-extended)
- File uploads (resumes) saved to /uploads
- Admin dashboard using Flask-Admin
- Scheduled job example using APScheduler
- Simple analytics event endpoint
- OpenAI call placeholder (configure OPENAI_API_KEY in env)
- Dockerfile and Procfile for Render deployment

Quick start (local):
1. python -m venv venv && source venv/bin/activate
2. pip install -r requirements.txt
3. cp .env.example .env and edit variables
4. flask db init (not included migrations) or simply run: python app.py
5. Visit http://127.0.0.1:5000/

Files of interest:
- app.py            : app factory + route registration
- models.py         : SQLAlchemy models
- auth.py           : auth routes (register/login/me)
- guidance.py       : sample guidance/ai endpoints
- admin.py          : flask-admin setup
- tasks.py          : scheduled job example
- uploads/          : where resumes will be stored
