"""Model package — importing it registers every mapper.

SQLAlchemy resolves ``relationship("User")`` targets by name, so a module that is
never imported means a mapper that is never configured. Importing this package is
therefore what makes ``Base.metadata`` complete, which is in turn what makes
``alembic revision --autogenerate`` see the whole schema.

``test_ml_isolation.py`` and a plain count assert the 14 tables this produces.
"""

from app.db.base import Base
from app.models.audit import AuditLog
from app.models.auth_token import AuthToken, TokenPurpose
from app.models.education import Certification, EducationRecord
from app.models.feedback import Feedback
from app.models.interview import InterviewExchange, InterviewSession
from app.models.job import JobRole, JobRoleSkill
from app.models.profile import Profile
from app.models.project import Project
from app.models.rate_limit_event import RateLimitEvent
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.recommendation_feedback import (
    FeedbackAction,
    RecommendationFeedback,
)
from app.models.resume import ResumeDetectedSkill, ResumeUpload
from app.models.roadmap import LearningRoadmap, LearningRoadmapTask
from app.models.skill import SKILL_CATEGORIES, Skill, SkillAlias
from app.models.user import User, UserRole
from app.models.user_skill import SkillSource, UserSkill
from app.models.work_history import WorkHistory, WorkHistorySource

__all__ = [
    "SKILL_CATEGORIES",
    "AuditLog",
    "AuthToken",
    "Base",
    "Certification",
    "EducationRecord",
    "Feedback",
    "FeedbackAction",
    "InterviewExchange",
    "InterviewSession",
    "JobRole",
    "JobRoleSkill",
    "LearningRoadmap",
    "LearningRoadmapTask",
    "Profile",
    "Project",
    "RateLimitEvent",
    "RecommendationFeedback",
    "RecommendationResult",
    "RecommendationRun",
    "ResumeDetectedSkill",
    "ResumeUpload",
    "Skill",
    "SkillAlias",
    "SkillSource",
    "TokenPurpose",
    "User",
    "UserRole",
    "UserSkill",
    "WorkHistory",
    "WorkHistorySource",
]

#: The 14-table core from proposal section 6.1, plus the extras that are not
#: proposal requirements: `feedback` (alembic/versions/0003_feedback.py),
#: `audit_log` (alembic/versions/0005_audit_log.py), and `rate_limit_event`
#: (alembic/versions/0009_rate_limit_event.py), which makes the rate limit a
#: deployment-wide limit rather than a per-process one.
CORE_TABLE_COUNT = 14
TOTAL_TABLE_COUNT = 24

