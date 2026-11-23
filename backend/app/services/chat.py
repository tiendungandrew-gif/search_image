"""Chat authorization and safe attachment preparation."""

import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import or_, select

from app.core.exceptions import AppError
from app.db.models.chat import Conversation

MAX_CHAT_IMAGE = 10 * 1024 * 1024


def participant_clause(user_id):
    return or_(Conversation.member_a == user_id, Conversation.member_b == user_id)


async def conversation_for(session, conversation_id, user_id, *, lock=False):
    statement = select(Conversation).where(
        Conversation.id == conversation_id, participant_clause(user_id)
    )
    if lock:
        statement = statement.with_for_update()
    conversation = await session.scalar(statement)
    if conversation is None:
        raise AppError(404, "CHAT_NOT_FOUND", "Không tìm thấy cuộc trò chuyện")
    return conversation


def prepare_chat_image(data):
    if not data or len(data) > MAX_CHAT_IMAGE:
        raise AppError(413, "CHAT_IMAGE_TOO_LARGE", "Ảnh tối đa 10 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("unsupported image")
                if original.width * original.height > 25_000_000:
                    raise ValueError("too many pixels")
                original.load()
                image = ImageOps.exif_transpose(original)
                image.thumbnail((1920, 1920))
                rgb = Image.new("RGB", image.size, "white")
                if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                    rgba = image.convert("RGBA")
                    rgb.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    rgb.paste(image.convert("RGB"))
                output = io.BytesIO()
                rgb.save(output, format="JPEG", quality=85, optimize=True)
                rgb.close()
                return output.getvalue()
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise AppError(
            422, "INVALID_CHAT_IMAGE", "Chọn ảnh JPEG, PNG hoặc WebP, tối đa 25 megapixel"
        ) from None


def message_snapshot(message):
    return {
        "id": str(message.id),
        "sender_id": str(message.sender_id),
        "client_id": str(message.client_id),
        "body": message.body,
        "created_at": message.created_at.isoformat(),
        "image_url": f"/api/v1/chat/attachments/{message.id}" if message.image_key else None,
    }
