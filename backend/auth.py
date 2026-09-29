from flask import Blueprint, request, jsonify, current_app
from extensions import db, jwt
from models import User, Profile
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'email and password required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'email already exists'}), 400
    u = User(name=name, email=email)
    u.set_password(password)
    try:
        db.session.add(u)
        db.session.commit()
        # create empty profile
        p = Profile(user_id=u.id)
        db.session.add(p)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Failed to create user and profile')
        return jsonify({'error': 'internal server error'}), 500
    token = create_access_token(identity=str(u.id))
    return jsonify({'user': u.to_dict(), 'token': token})

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'invalid credentials'}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({'user': user.to_dict(), 'token': token})

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = User.query.get(uid)
    if not user:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'user': user.to_dict()})
