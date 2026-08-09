from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey

from ..database import Base


class AirbnbSearch(Base):
    """A cached Bright Data "discover Airbnb by location" job (see
    routers/airbnb_search.py). Bright Data itself has no result-caching -
    every trigger call burns real quota against the free 5K
    records/month tier - so unlike the AsiaYo proxy (which relies on that
    service's own 60-minute cache), this app owns the cache: a repeat
    search for the exact same locations/dates/adults within
    airbnb_search_cache_days (see config.py) returns this stored row
    instead of triggering a fresh Bright Data collection.

    location: JSON-encoded, sorted list of location strings (a search can
    cover multiple locations in one Bright Data call - see
    _trigger_body/_location_key in the router), not a single string.

    status: "pending" while waiting for the background task to even
    trigger Bright Data, "scraping" once triggered and Bright Data's
    snapshot is running/closing, "done" once results are parsed in,
    "failed" if Bright Data errored out. results is the parsed listing
    array, JSON-encoded (not every raw Bright Data field - see
    _extract_listing in the router - the full response is very large and
    mostly irrelevant to the UI).

    children/infants/pets/currency aren't exposed as search inputs (kept
    as columns with fixed defaults - currency is always "TWD", the other
    three are always 0 - simpler than a schema migration to drop them,
    and cheap to revive later if ever needed)."""

    __tablename__ = "airbnb_searches"

    id = Column(Integer, primary_key=True)
    location = Column(Text, nullable=False, index=True)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    adults = Column(Integer, nullable=False, default=1)
    children = Column(Integer, nullable=False, default=0)
    infants = Column(Integer, nullable=False, default=0)
    pets = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="TWD")
    snapshot_id = Column(String(64), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # "pending" | "scraping" | "done" | "failed"
    results = Column(Text, nullable=True)  # JSON-encoded list
    error_message = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
