from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..services.bash_reference_service import parse_command

router = APIRouter(prefix="/api/bash-reference", tags=["bash-reference"])


class BashCommandOut(BaseModel):
    command: str
    description: str

    class Config:
        from_attributes = True


class ParseRequest(BaseModel):
    command: str


class ParseResponse(BaseModel):
    explanation: str


@router.get("/search", response_model=list[BashCommandOut])
def search_commands(
    q: str = "", db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """指令查詢頁的搜尋框(見 BashReferenceView.js)- q 為空就不回傳(還沒
    開始打字),否則用 command 欄位做不分大小寫的子字串搜尋,完全相符的排
    最前面。"""
    q = q.strip()
    if not q:
        return []
    like = f"%{q}%"
    rows = (
        db.query(models.BashCommand)
        .filter(or_(models.BashCommand.command.ilike(like), models.BashCommand.description.ilike(like)))
        .order_by(models.BashCommand.command)
        .limit(500)  # 排相關性排序用的候選集上限,遠大於實際會顯示的數量
        .all()
    )
    ql = q.lower()
    rows.sort(key=lambda r: (r.command.lower() != ql, not r.command.lower().startswith(ql)))
    return rows[:30]


@router.post("/parse", response_model=ParseResponse)
def parse_command_route(payload: ParseRequest, user: models.User = Depends(get_current_user)):
    """指令查詢頁的第二個欄位 - 貼一整串指令,讓 LLM 解析整體作用(不查字
    典表,獨立的一次性 LLM 呼叫,見 bash_reference_service.py)。"""
    return {"explanation": parse_command(payload.command)}
