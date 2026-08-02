from fastapi import APIRouter

from ..agent import model_catalog
from ..schemas.chat import ModelInfo

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelInfo])
def list_models():
    return model_catalog.list_models()
