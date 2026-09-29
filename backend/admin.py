from flask_admin.contrib.sqla import ModelView
from models import User, Profile, Upload, GuidanceSession, Event, Feedback
from extensions import admin, db
from markupsafe import Markup
import json


class FeedbackModelView(ModelView):
    # show important columns and a pretty-printed features column
    column_list = ('id', 'created_at', 'name', 'email', 'subject', 'feedback_type', 'rating', 'allow_contact', 'features_json')
    column_searchable_list = ('name', 'email', 'subject', 'message')
    column_filters = ('feedback_type', 'rating', 'allow_contact', 'created_at')
    form_excluded_columns = ('features_json',)
    can_create = False
    can_edit = False
    can_delete = True

    def _format_features(self, context, model, name):
        try:
            j = json.loads(getattr(model, name) or 'null')
            pretty = json.dumps(j, indent=2, ensure_ascii=False)
            return Markup(f'<pre style="white-space:pre-wrap">{pretty}</pre>')
        except Exception:
            return getattr(model, name) or ''

    column_formatters = {
        'features_json': lambda v, c, m, p: FeedbackModelView._static_format_features(m)
    }

    @staticmethod
    def _static_format_features(model):
        try:
            j = json.loads(model.features_json) if model.features_json else None
            pretty = json.dumps(j, indent=2, ensure_ascii=False)
            return Markup(f'<pre style="white-space:pre-wrap">{pretty}</pre>')
        except Exception:
            return model.features_json or ''


def init_admin(app):
    # Only add views (do not call admin.init_app here — app.py already does that)
    # To avoid duplicate views on hot reloads, clear existing views first if present.
    try:
        # remove existing views if any (safe for dev)
        admin._views = []
    except Exception:
        pass

    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Profile, db.session))
    admin.add_view(ModelView(Upload, db.session))
    admin.add_view(ModelView(GuidanceSession, db.session))
    admin.add_view(ModelView(Event, db.session))
    admin.add_view(FeedbackModelView(Feedback, db.session))
