from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey

from ..database import Base


class AirbnbSearch(Base):
    """A cached Apify "automation-lab/airbnb-listing" actor run (see
    routers/airbnb_search.py). Apify itself has no result-caching -
    every run call burns real platform credit - so unlike the AsiaYo proxy
    (which relies on that service's own 60-minute cache), this app owns the
    cache: a repeat search for the exact same locations/dates/adults within
    airbnb_search_cache_days (see config.py) returns this stored row
    instead of triggering a fresh Apify run.

    location: JSON-encoded, sorted list of location strings (maps directly
    to the actor's locationQueries input array - see _trigger_body/
    _location_key in the router), not a single string.

    status: "pending" while waiting for the background task to even start
    the Apify run, "scraping" once started and the run is still
    READY/RUNNING, "done" once results are parsed in, "failed" if the run
    errored/timed out/was aborted. results is the parsed listing array,
    JSON-encoded (not every raw Apify field - see _extract_listing in the
    router).

    snapshot_id holds the Apify run id (column name kept from the earlier
    Bright Data integration to avoid a migration - it's just an opaque job
    id either way).

    children/infants/pets/currency aren't exposed as search inputs (kept
    as columns with fixed defaults - currency is always "USD" (Apify's
    input schema has no TWD option), the other three are always 0 -
    simpler than a schema migration to drop them, and cheap to revive
    later if ever needed)."""

    __tablename__ = "airbnb_searches"

    id = Column(Integer, primary_key=True)
    location = Column(Text, nullable=False, index=True)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    adults = Column(Integer, nullable=False, default=1)
    children = Column(Integer, nullable=False, default=0)
    infants = Column(Integer, nullable=False, default=0)
    pets = Column(Integer, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="USD")
    snapshot_id = Column(String(64), nullable=True)  # Apify run id
    status = Column(String(20), nullable=False, default="pending")  # "pending" | "scraping" | "done" | "failed"
    results = Column(Text, nullable=True)  # JSON-encoded list
    error_message = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
