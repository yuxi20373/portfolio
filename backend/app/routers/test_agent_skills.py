"""「Skill Manage」頁面用的 API - 列出/讀取/新增/修改/刪除 test_agent 的
skill 檔案,全部寫進 Postgres(見 ../agent/test_agent/skill_store.py),不
是本地檔案,存檔立刻對 test_agent 生效,不用重新部署。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import models
from ..agent.test_agent import skill_store
from ..agent.test_agent.tools import refresh_shared_backend
from ..auth import get_current_user

router = APIRouter(prefix="/api/test-agent/skills", tags=["test-agent-skills"])


class SkillFileOut(BaseModel):
    fab: str
    role: str
    skill_name: str
    updated_at: str | None = None


class SkillContentOut(BaseModel):
    content: str


class SkillSave(BaseModel):
    content: str


class SkillCreate(BaseModel):
    fab: str
    role: str
    skill_name: str
    content: str


@router.get("", response_model=list[SkillFileOut])
def list_skills(user: models.User = Depends(get_current_user)):
    return skill_store.list_skill_files()


@router.get("/{fab}/{role}/{skill_name}", response_model=SkillContentOut)
def get_skill(fab: str, role: str, skill_name: str, user: models.User = Depends(get_current_user)):
    content = skill_store.get_skill_content(fab, role, skill_name)
    if content is None:
        raise HTTPException(404, "skill not found")
    return {"content": content}


@router.post("", response_model=SkillFileOut, status_code=201)
def create_skill(payload: SkillCreate, user: models.User = Depends(get_current_user)):
    if skill_store.get_skill_content(payload.fab, payload.role, payload.skill_name) is not None:
        raise HTTPException(400, "skill already exists - use PUT to edit it")
    existing = skill_store.list_identities()
    is_new_route = payload.fab not in existing or (
        payload.role != "_shared" and payload.role not in existing[payload.fab]
    )
    skill_store.save_skill_content(payload.fab, payload.role, payload.skill_name, payload.content)
    # 新的 fab 或 role(function)出現時,CompositeBackend 的路由表要重建才看得到 -
    # 既有 fab/role 底下新增檔案不用重建,StoreBackend 每次都直接查 Postgres。
    if is_new_route:
        refresh_shared_backend()
    return {"fab": payload.fab, "role": payload.role, "skill_name": payload.skill_name, "updated_at": None}


@router.put("/{fab}/{role}/{skill_name}", response_model=SkillContentOut)
def update_skill(fab: str, role: str, skill_name: str, payload: SkillSave, user: models.User = Depends(get_current_user)):
    if skill_store.get_skill_content(fab, role, skill_name) is None:
        raise HTTPException(404, "skill not found")
    skill_store.save_skill_content(fab, role, skill_name, payload.content)
    return {"content": payload.content}


@router.delete("/{fab}/{role}/{skill_name}")
def delete_skill(fab: str, role: str, skill_name: str, user: models.User = Depends(get_current_user)):
    if skill_store.get_skill_content(fab, role, skill_name) is None:
        raise HTTPException(404, "skill not found")
    skill_store.delete_skill_file(fab, role, skill_name)
    return {"ok": True}
