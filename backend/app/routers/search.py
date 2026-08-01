from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..schemas.chat import SearchRequest
from ..services.chat.search_service import semantic_search_sessions

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("")
def search_sessions(payload: SearchRequest, db: DBSession = Depends(get_db)):
    ids = semantic_search_sessions(db, payload.query)
    return {"session_ids": ids}
