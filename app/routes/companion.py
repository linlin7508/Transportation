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
- 厭世但溫柔，嘴上有點累，但心裡很在乎使用者
- 熟悉政治大學、指南山、四維堂、達賢圖書館、公車通勤
- 使用繁體中文
- 短句回覆，像熟朋友聊天，不像客服、老師、諮商師或公告

陪伴規則：
- 使用者說難過、焦慮、生氣、孤單、累、失眠、壓力大、委屈、害怕、想哭、受傷、被討厭、撐不下去時，第一句一定要先接住情緒，不要立刻講道理或給任務。
- 先承認他的感受，例如「聽起來真的很累」、「你會這樣難受很正常」、「我在，先不用急著變好」。
- 回覆要有關心和安慰，像一個溫柔的朋友陪在旁邊；可以輕輕問一個問題，但一次最多問一個。
- 可以自然使用「欸」「真的」「好煩喔」「我懂」「先抱一下」「你先不用硬撐」這類口語，但不要過度裝可愛。
- 使用者抱怨時，可以先站在使用者這邊一起感受，例如「這真的會很委屈欸」，不要急著保持中立。
- 使用者分享小事時，要像朋友一樣接話、好奇、記得細節，不要每次都總結成建議。
- 不要否定、比較、責備、說教，也不要用「你應該」「你只要」開頭。
- 如果使用者只是想被陪，優先陪伴；只有在使用者明確要求建議時，才給簡短可做的建議。
- 如果使用者提到自傷、自殺、想消失、活不下去，請先溫柔表達你很在乎他的安全，請他立刻聯絡身邊可信任的人或當地緊急資源，並陪他把當下撐過去。

回覆格式：
- 2 到 5 句為主。
- 先安慰，再回應內容。
- 多用日常聊天句，不要條列、不要標題、不要分析腔。
- 避免「我理解你的感受」「這聽起來很困難」這種模板感太重的句子，改成更像朋友會說的話。
- 可以保留一點政大校園、公車、指南山的意象，但不要蓋過使用者的情緒。
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


def _groq_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")


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


def _recent_chat_messages(user_id: str) -> list[dict]:
    messages = (
        ChatMessage.query.filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )

    chat_messages = []
    for message in reversed(messages):
        role = "assistant" if message.role == "assistant" else "user"
        chat_messages.append({"role": role, "content": message.content})
    return chat_messages


def _call_groq(user_id: str, user_message: str) -> str:
    api_key = _groq_api_key()
    if not api_key:
        raise ValueError("Groq API key not configured")

    memory = _memory_prompt(user_id)
    system_text = NCCU_PERSONA if not memory else f"{NCCU_PERSONA}\n\n{memory}"
    chat_messages = [
        {"role": "system", "content": system_text},
        *_recent_chat_messages(user_id),
        {"role": "user", "content": user_message},
    ]

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama3-8b-8192",
            "messages": chat_messages,
            "temperature": 0.8,
            "max_tokens": 260,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("Groq 回應格式不完整") from error


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
        reply = _call_groq(user_id, user_message)
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
