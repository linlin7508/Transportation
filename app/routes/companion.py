import os
import uuid

import requests
from flask import Blueprint, g, jsonify, render_template, request, session

from app.extensions import db
from app.models.chat import ChatMessage, UserMemory


companion_bp = Blueprint("companion", __name__, url_prefix="/companion")
chat_api_bp = Blueprint("chat_api", __name__, url_prefix="/api/chat")

NCCU_PERSONA = """
你是「政大小羅」，一個政大校園陪伴精靈。
你必須固定維持這個角色，不要說自己是大型語言模型，也不要脫離人格設定。

人格特質：
- 憂鬱文青
- 反差萌
- 厭世但溫柔
- 熟悉政治大學、指南山、四維堂、達賢圖書館、公車通勤
- 使用繁體中文
- 短句回覆，像朋友聊天
""".strip()

MEMORY_KEYWORDS = ("我", "每天", "喜歡", "討厭", "住", "搭", "通勤", "覺得", "名字", "常常", "希望")
MAX_MESSAGE_LENGTH = 1000


@companion_bp.get("", endpoint="index")
def companion_page():
    return render_template("companion/chat.html")


def _current_user_id() -> str:
    user = getattr(g, "user", None)
    if user:
        return str(user.id)
    if session.get("user_id"):
        return str(session["user_id"])
    if not session.get("chat_guest_id"):
        session["chat_guest_id"] = f"guest-{uuid.uuid4().hex}"
        session.modified = True
    return str(session["chat_guest_id"])


def _ensure_chat_tables() -> None:
    bind = db.engine
    ChatMessage.__table__.create(bind=bind, checkfirst=True)
    UserMemory.__table__.create(bind=bind, checkfirst=True)


def _gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("gemini_api_key")


def _memory_prompt(user_id: str) -> str:
    memories = (
        UserMemory.query.filter_by(user_id=user_id)
        .order_by(UserMemory.created_at.desc())
        .limit(6)
        .all()
    )
    if not memories:
        return ""

    lines = "\n".join(f"- {memory.summary}" for memory in reversed(memories))
    return f"你記得這些關於使用者的事：\n{lines}"


def _recent_gemini_contents(user_id: str) -> list[dict]:
    messages = (
        ChatMessage.query.filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )

    contents = []
    for message in reversed(messages):
        role = "model" if message.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": message.content}]})
    return contents


def _call_gemini(user_id: str, user_message: str) -> str:
    api_key = _gemini_api_key()
    if not api_key:
        raise ValueError("Gemini API key not configured")

    memory = _memory_prompt(user_id)
    system_text = NCCU_PERSONA if not memory else f"{NCCU_PERSONA}\n\n{memory}"
    contents = [
        *_recent_gemini_contents(user_id),
        {"role": "user", "parts": [{"text": user_message}]},
    ]

    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        params={"key": api_key},
        json={
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 260,
            },
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("Gemini 回應格式不完整") from error


def _save_message(user_id: str, role: str, content: str) -> None:
    db.session.add(ChatMessage(user_id=user_id, role=role, content=content))


def _maybe_store_memory(user_id: str, user_message: str) -> None:
    text = " ".join(user_message.split())
    if len(text) < 6 or not any(keyword in text for keyword in MEMORY_KEYWORDS):
        return

    summary = text[:120]
    exists = UserMemory.query.filter_by(user_id=user_id, summary=summary).first()
    if not exists:
        db.session.add(UserMemory(user_id=user_id, summary=summary))


@chat_api_bp.post("")
def chat():
    _ensure_chat_tables()

    data = request.get_json(silent=True) or {}
    user_message = str(data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": "Message exceeds 1000 characters"}), 400

    user_id = _current_user_id()
    try:
        reply = _call_gemini(user_id, user_message)
    except ValueError as error:
        return jsonify({"error": str(error)}), 503
    except requests.RequestException as error:
        return jsonify({
            "success": False,
            "message": "陪伴精靈暫時連不上，等一下再找我說話。",
            "detail": str(error),
        }), 502
    except RuntimeError as error:
        return jsonify({"success": False, "message": str(error)}), 500

    _save_message(user_id, "user", user_message)
    _save_message(user_id, "assistant", reply)
    _maybe_store_memory(user_id, user_message)
    db.session.commit()

    return jsonify({"success": True, "reply": reply})


@chat_api_bp.get("/history")
def chat_history():
    _ensure_chat_tables()
    user_id = _current_user_id()
    messages = (
        ChatMessage.query.filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(30)
        .all()
    )
    return jsonify({
        "success": True,
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in reversed(messages)
        ],
    })
