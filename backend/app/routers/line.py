import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..integrations import line_client
from ..services.chat.chat_service import get_or_create_session, process_chat_message

logger = logging.getLogger("line_webhook")
router = APIRouter(prefix="/api/line", tags=["line"])


@router.post("/webhook")
async def line_webhook(request: Request, db: DBSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not line_client.verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="invalid signature")

    payload = await request.json()
    events = payload.get("events", [])

    for event in events:
        if event.get("type") != "message":
            continue
        message = event.get("message", {})
        if message.get("type") != "text":
            continue

        user_text = message.get("text", "")
        line_user_id = event.get("source", {}).get("userId")
        reply_token = event.get("replyToken")

        if not line_user_id:
            continue

        session = get_or_create_session(db, channel="line", external_user_id=line_user_id)
        try:
            reply_text = process_chat_message(db, session, user_text)
        except Exception as ex:
            logger.exception("Failed to process LINE message")
            reply_text = f"Sorry, something went wrong: {ex}"

        if reply_token:
            line_client.reply(reply_token, reply_text)

    return {"status": "ok"}
