from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.timezone import local_today
from app.models.models import ActivityLog


def record_activity(db: Session, user_id: int, tz: ZoneInfo) -> None:
    """Mark today (in the user's timezone) as a study day. Adds the row to the
    session if it's missing; the caller commits."""
    today = local_today(tz)
    exists = (
        db.query(ActivityLog.id)
        .filter(ActivityLog.user_id == user_id, ActivityLog.date_string == today)
        .first()
    )
    if exists is None:
        db.add(ActivityLog(user_id=user_id, date_string=today))
