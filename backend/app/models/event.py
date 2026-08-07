from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey

from ..database import Base


class CalendarEvent(Base):
    """A user-created Event or Reminder, shown on the Calendar page (see
    routers/events.py for CRUD, routers/calendar.py for how they're folded
    into the month/day read endpoints).

    kind: "event" (always shown, never expires) or "reminder" (has a
    specific remind_at moment; once that passes it's "expired" - dropped
    from the month grid's per-day chip preview, but still shown in that
    day's detail list, just grayed out and sorted to the bottom). Expiry
    isn't a stored flag - it's computed at read time from remind_at vs. now,
    since "now" obviously isn't a fixed value.

    event_date: which day cell it's filed under (a plain calendar date, not
    a timestamp - deliberately timezone-naive, same idea as Note's date
    grouping elsewhere in this app)."""

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    kind = Column(String(20), nullable=False)  # "event" | "reminder"
    event_date = Column(Date, nullable=False, index=True)
    remind_at = Column(DateTime, nullable=True)  # only set when kind == "reminder"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
