from flask import Blueprint, request, jsonify, current_app, send_from_directory
from extensions import db
from models import GuidanceSession, Upload, User
from flask_jwt_extended import jwt_required, get_jwt_identity
import os, uuid, json, requests, re

guidance_bp = Blueprint('guidance', __name__)

@guidance_bp.route('/upload_resume', methods=['POST'])
@jwt_required(optional=True)
def upload_resume():
    uid = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    f = request.files['file']
    filename = f.filename
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    f.save(path)
    up = Upload(user_id=uid, filename=filename, filepath=path)
    try:
        db.session.add(up)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to save upload record')
        return jsonify({'error': 'internal server error'}), 500
    return jsonify({'upload_id': up.id, 'filename': filename})

@guidance_bp.route('/uploads/<int:upload_id>', methods=['GET'])
def download_upload(upload_id):
    up = Upload.query.get(upload_id)
    if not up:
        return jsonify({'error':'not found'}), 404
    directory = os.path.dirname(up.filepath)
    return send_from_directory(directory, os.path.basename(up.filepath), as_attachment=True)

@guidance_bp.route('/ai/recommend', methods=['POST'])
@jwt_required(optional=True)
def ai_recommend():
    data = request.json or {}
    profile = data.get('profile') or {}
    goals = data.get('goals') or ''
    # simple placeholder: call OpenAI if key present, otherwise return mock
    key = os.getenv('OPENAI_API_KEY') or current_app.config.get('OPENAI_API_KEY')
    prompt = f"Make a short career recommendation for goals: {goals} and profile: {profile}"
    result = {'recommendation': 'mock suggestion: build projects, learn data structures, apply to internships'}
    if key:
        try:
            headers = {'Authorization': f'Bearer {key}', 'Content-Type':'application/json'}
            # This is a placeholder. The real api call depends on the model/provider.
            payload = { 'model': 'gpt-4o-mini', 'input': prompt }
            resp = requests.post('https://api.openai.com/v1/responses', headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                j = resp.json()
                result['recommendation'] = j.get('output') or j
            else:
                result['api_error'] = resp.text
        except Exception as e:
            result['error'] = str(e)
    # save session
    gs = GuidanceSession(user_id=get_jwt_identity(), inputs_json=json.dumps({'profile':profile,'goals':goals}), result_json=json.dumps(result))
    try:
        db.session.add(gs)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to create GuidanceSession')
        return jsonify({'error': 'internal server error'}), 500
    return jsonify({'session_id': gs.id, 'result': result})

@guidance_bp.route('/analytics/event', methods=['POST'])
@guidance_bp.route('/analytics/event', methods=['POST'])
@jwt_required(optional=True)
def analytics_event():
    data = request.json or {}
    name = data.get('name')
    metadata = data.get('metadata', {})
    uid = get_jwt_identity()
    from models import Event
    ev = Event(user_id=uid, name=name, metadata_json=json.dumps(metadata))
    try:
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to save analytics event')
        return jsonify({'error': 'internal server error'}), 500
    return jsonify({'status':'ok', 'event_id': ev.id})


@guidance_bp.route('/feedback', methods=['POST'])
@jwt_required(optional=True)
def submit_feedback():
    data = request.json or {}
    name = data.get('name')
    email = data.get('email')
    feedback_type = data.get('feedbackType') or data.get('feedback_type') or data.get('type')
    rating = data.get('rating')
    subject = data.get('subject')
    message = data.get('message')
    features = data.get('features') or []
    allow_contact = bool(data.get('allowContact') or data.get('allow_contact'))
    uid = get_jwt_identity()
    from models import Feedback
    # Basic validation
    errors = []
    if not message or not str(message).strip():
        errors.append('message is required')
    if subject and len(subject) > 256:
        errors.append('subject too long (max 256 chars)')
    if message and len(message) > 5000:
        errors.append('message too long (max 5000 chars)')
    if email:
        # simple email regex
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            errors.append('email invalid')
    if rating is not None:
        try:
            r_int = int(rating)
            if r_int < 0 or r_int > 5:
                errors.append('rating must be between 0 and 5')
        except Exception:
            # allow string ratings but warn
            pass
    if errors:
        return jsonify({'error': 'invalid request', 'details': errors}), 400

    try:
        fb = Feedback(
            user_id=uid,
            name=(name or '').strip() or None,
            email=(email or '').strip() or None,
            feedback_type=(feedback_type or '').strip() or None,
            rating=str(rating) if rating is not None else None,
            subject=(subject or '').strip() or None,
            message=(message or '').strip() or None,
            features_json=json.dumps(features),
            allow_contact=bool(allow_contact)
        )
        db.session.add(fb)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to save feedback')
        return jsonify({'error': 'internal server error'}), 500
    return jsonify({'status':'ok', 'feedback_id': fb.id})


@guidance_bp.route('/feedbacks', methods=['GET'])
@jwt_required()
def list_feedbacks():
    """Admin-only: list feedback entries with pagination and optional filtering."""
    uid = get_jwt_identity()
    # check user role
    user = None
    try:
        user = User.query.get(uid)
    except Exception:
        current_app.logger.exception('Failed to load user for feedbacks list')
    if not user or getattr(user, 'role', 'user') != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 25))
    except Exception:
        per_page = 25
    q = Feedback.query.order_by(Feedback.created_at.desc())
    # optional filters
    f_type = request.args.get('type') or request.args.get('feedback_type')
    if f_type:
        q = q.filter(Feedback.feedback_type == f_type)
    user_filter = request.args.get('user_id')
    if user_filter:
        try:
            q = q.filter(Feedback.user_id == int(user_filter))
        except Exception:
            pass

    total = q.count()
    items = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({'total': total, 'page': page, 'per_page': per_page, 'items': [i.to_dict() for i in items]})
