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

    mirror_code = user_data.get(user_id, {}).get("mirror_code")
    if not mirror_code:
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

        resp = requests.post(f"{FREDI_API_BASE}/api/mirrors/complete", json=payload, timeout=15)
        logger.info(f"🪞 Mirror complete: {mirror_code} -> {resp.status_code}")

        # Очищаем mirror_code после использования
        user_data.get(user_id, {}).pop("mirror_code", None)
    except Exception as e:
        logger.error(f"🪞 Mirror complete error: {e}")
