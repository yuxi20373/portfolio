import base64
import io
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/emoji", tags=["emoji"])

EMOJI_SIZE = 128  # px, square bounding box - sharp enough at typical inline sizes, small enough to store cheaply in the DB
SHORTCODE_RE = re.compile(r"^[a-zA-Z0-9_+-]+$")


def _emoji_dict(e: models.CustomEmoji):
    # image_data (base64) deliberately left out - the frontend fetches the
    # actual bytes via url, this dict is just for the picker/manage list.
    return {"id": e.id, "shortcode": e.shortcode, "url": f"/api/emoji/{e.id}/image"}


@router.get("")
def list_emoji(db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    items = (
        db.query(models.CustomEmoji)
        .filter(models.CustomEmoji.user_id == user.id)
        .order_by(models.CustomEmoji.shortcode.asc())
        .all()
    )
    return [_emoji_dict(e) for e in items]


@router.post("")
async def upload_emoji(
    shortcode: str = Form(...),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    shortcode = shortcode.strip().lower()
    if not shortcode or not SHORTCODE_RE.match(shortcode):
        raise HTTPException(400, "Shortcode can only contain letters, numbers, _, - and +")

    from PIL import Image  # 只有這裡用得到,延遲載入避免拖慢整個 app 的啟動

    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        raise HTTPException(400, "Couldn't read that as an image")

    img.thumbnail((EMOJI_SIZE, EMOJI_SIZE))  # 等比縮小到 128x128 以內,不強制裁成正方形 - 顯示時用 CSS object-fit 處理
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

    # 同一個使用者重複上傳同名 shortcode 就直接取代舊圖,而不是報錯或並存。
    existing = (
        db.query(models.CustomEmoji)
        .filter(models.CustomEmoji.user_id == user.id, models.CustomEmoji.shortcode == shortcode)
        .first()
    )
    if existing:
        existing.image_data = encoded
        e = existing
    else:
        e = models.CustomEmoji(shortcode=shortcode, image_data=encoded, user_id=user.id)
        db.add(e)

    db.commit()
    db.refresh(e)
    return _emoji_dict(e)


@router.get("/{emoji_id}/image")
def get_emoji_image(emoji_id: int, db: DBSession = Depends(get_db)):
    # 刻意不接 get_current_user - 這是給 <img src> 直接載入的,瀏覽器不會附
    # Authorization header。圖片本身只是裝飾用的小 emoji,不是敏感資料,公開
    # 讀取(要知道確切的數字 id 才拿得到)在這裡是合理的取捨。
    e = db.query(models.CustomEmoji).get(emoji_id)
    if not e:
        raise HTTPException(404, "not found")
    return Response(content=base64.b64decode(e.image_data), media_type="image/png")


@router.delete("/{emoji_id}")
def delete_emoji(emoji_id: int, db: DBSession = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = db.query(models.CustomEmoji).get(emoji_id)
    if not e or e.user_id != user.id:
        raise HTTPException(404, "not found")
    db.delete(e)
    db.commit()
    return {"ok": True}
