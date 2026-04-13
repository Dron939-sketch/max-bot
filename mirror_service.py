"""
mirror_service.py — Завершает зеркальный тест когда друг проходит тест в боте.
Вызывает POST /api/mirrors/complete на бэкенде Фреди.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

FREDI_API_BASE = os.environ.get("FREDI_API_BASE", "https://fredi-backend-flz2.onrender.com")


def complete_mirror_if_needed_sync(user_id: int, user_data_dict: dict):
    """Если пользователь пришёл по mirror-ссылке, отправляем результаты владельцу зеркала."""
    from state import user_data, user_names

    # Сначала проверяем локально (если /start mirror_ попал в polling)
    mirror_code = user_data.get(user_id, {}).get("mirror_code")
    logger.info(f"🪞 [MIRROR] complete check: user={user_id}, local_mirror_code={mirror_code}")

    # Если нет локально — проверяем базу (mirror_code сохранён через Frederick webhook)
    if not mirror_code:
        mirror_code = _check_db_for_mirror(user_id)
        logger.info(f"🪞 [MIRROR] DB fallback: user={user_id}, db_mirror_code={mirror_code}")

    if not mirror_code:
        logger.info(f"🪞 [MIRROR] No mirror_code found for user={user_id}, skipping")
        return

    try:
        vectors = {}
        for k, levels in (user_data_dict.get("behavioral_levels") or {}).items():
            vectors[k] = sum(levels) / len(levels) if levels else 3.0

        profile_data = user_data_dict.get("profile_data") or {}
        user_name = user_names.get(user_id, "Друг")

        payload = {
            "mirror_code": mirror_code,
            "friend_user_id": user_id,
            "friend_name": user_name,
            "friend_profile_code": profile_data.get("display_name") if isinstance(profile_data, dict) else None,
            "friend_vectors": vectors,
            "friend_deep_patterns": user_data_dict.get("deep_patterns") or {},
            "friend_ai_profile": user_data_dict.get("ai_generated_profile", ""),
            "friend_perception_type": user_data_dict.get("perception_type"),
            "friend_thinking_level": user_data_dict.get("thinking_level"),
        }

        logger.info(f"🪞 [MIRROR] Sending to {FREDI_API_BASE}/api/mirrors/complete: code={mirror_code}, user={user_id}, vectors={vectors}")

        resp = requests.post(f"{FREDI_API_BASE}/api/mirrors/complete", json=payload, timeout=15)
        body = resp.text[:200]
        logger.info(f"🪞 [MIRROR] Response: {mirror_code} -> HTTP {resp.status_code}, body={body}")

        # Очищаем mirror_code
        user_data.get(user_id, {}).pop("mirror_code", None)
    except Exception as e:
        logger.error(f"🪞 [MIRROR] Error completing mirror {mirror_code}: {e}", exc_info=True)


def _check_db_for_mirror(user_id: int):
    """Проверяет базу: есть ли активное зеркало где friend_user_id = этот пользователь."""
    try:
        resp = requests.get(
            f"{FREDI_API_BASE}/api/mirrors/pending/{user_id}",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            code = data.get("mirror_code")
            if code:
                logger.info(f"🪞 [MIRROR] Found pending mirror in DB: user={user_id}, code={code}")
                return code
    except Exception as e:
        logger.error(f"🪞 [MIRROR] DB mirror check error: {e}")
    return None
