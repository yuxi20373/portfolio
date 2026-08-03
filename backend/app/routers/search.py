from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..schemas.chat import SearchRequest
from ..services.chat.search_service import semantic_search_sessions

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("")
def search_sessions(
    payload: SearchRequest, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    ids = semantic_search_sessions(db, user.id, payload.query)
    return {"session_ids": ids}
