from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    headline = db.Column(db.String(256))
    skills = db.Column(db.Text)  # comma separated
    education = db.Column(db.Text)
    experience = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('profile', uselist=False))

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    filename = db.Column(db.String(256))
    filepath = db.Column(db.String(512))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class GuidanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    inputs_json = db.Column(db.Text)
    result_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(128))
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    feedback_type = db.Column(db.String(64))
    rating = db.Column(db.String(8))
    subject = db.Column(db.String(256))
    message = db.Column(db.Text)
    features_json = db.Column(db.Text)
    allow_contact = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        features = None
        try:
            features = json.loads(self.features_json) if self.features_json else None
        except Exception:
            features = self.features_json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'feedback_type': self.feedback_type,
            'rating': self.rating,
            'subject': self.subject,
            'message': self.message,
            'features': features,
            'allow_contact': bool(self.allow_contact),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
