"""Model package — importing it registers every mapper.

SQLAlchemy resolves ``relationship("User")`` targets by name, so a module that is
never imported means a mapper that is never configured. Importing this package is
therefore what makes ``Base.metadata`` complete, which is in turn what makes
``alembic revision --autogenerate`` see the whole schema.

``test_ml_isolation.py`` and a plain count assert the 14 tables this produces.
"""

from app.db.base import Base
from app.models.education import Certification, EducationRecord
from app.models.feedback import Feedback
from app.models.job import JobRole, JobRoleSkill
from app.models.profile import Profile
from app.models.project import Project
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.resume import ResumeDetectedSkill, ResumeUpload
from app.models.skill import SKILL_CATEGORIES, Skill, SkillAlias
from app.models.user import User, UserRole
from app.models.user_skill import SkillSource, UserSkill

__all__ = [
    "SKILL_CATEGORIES",
    "Base",
    "Certification",
    "EducationRecord",
    "Feedback",
    "JobRole",
    "JobRoleSkill",
    "Profile",
    "Project",
    "RecommendationResult",
    "RecommendationRun",
    "ResumeDetectedSkill",
    "ResumeUpload",
    "Skill",
    "SkillAlias",
    "SkillSource",
    "User",
    "UserRole",
    "UserSkill",
]

# The 14-table core from proposal section 6.1, plus the `feedback` extra
# (not a proposal requirement; see alembic/versions/0003_feedback.py).
CORE_TABLE_COUNT = 14
TOTAL_TABLE_COUNT = 15
