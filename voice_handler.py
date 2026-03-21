#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТЕЙШИЙ ОБРАБОТЧИК ГОЛОСА - ДЛЯ ДИАГНОСТИКИ
"""

import logging
import threading
import asyncio

logger = logging.getLogger(__name__)

def register_voice_handler(bot):
    """Регистрирует обработчик голоса"""
    
    @bot.message_handler(content_types=['voice'])
    def voice_receiver(message):
        """ПРОСТОЙ ОБРАБОТЧИК - ТОЛЬКО ЛОГИРУЕТ"""
        user_id = message.from_user.id
        
        # ЕДИНСТВЕННЫЙ ЛОГ
        logger.info(f"🎤🎤🎤 ГОЛОС ПОЛУЧЕН! user={user_id}, voice={message.voice}")
        
        # Отправляем простое сообщение
        bot.send_message(
            message.chat.id,
            "🎤 Голос получен! Обрабатываю..."
        )
    
    logger.info("✅ Voice handler registered")
    return voice_receiver
