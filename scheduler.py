#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Планировщик задач для MAX
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from bot_instance import bot
from message_utils import safe_send_message
from state import user_data, user_contexts, user_names

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Планировщик периодических задач"""
    
    def __init__(self):
        self.tasks = {}
        self.running = False
    
    def start(self):
        """Запускает планировщик"""
        if not self.running:
            self.running = True
            asyncio.create_task(self._run_scheduler())
            logger.info("✅ Планировщик задач запущен")
    
    async def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            now = datetime.now()
            
            # Проверяем задачи каждый час
            if now.minute == 0:
                await self._check_morning_messages()
            
            await asyncio.sleep(60)  # Проверка каждую минуту
    
    async def _check_morning_messages(self):
        """Проверяет и отправляет утренние сообщения"""
        now = datetime.now()
        
        # Отправляем в 9:00 утра
        if now.hour == 9:
            for user_id, context in user_contexts.items():
                if context and context.city:
                    await self._send_morning_message(user_id)
    
    async def _send_morning_message(self, user_id: int):
        """Отправляет утреннее сообщение пользователю"""
        try:
            context = user_contexts.get(user_id)
            user_name = user_names.get(user_id, "друг")
            
            # Обновляем погоду
            await context.update_weather()
            
            day_context = context.get_day_context()
            
            text = f"☀️ {bold('Доброе утро,')} {user_name}!\n\n"
            
            if context.weather_cache:
                weather = context.weather_cache
                text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n"
            
            text += f"\n{day_context['greeting']}\n\n"
            text += f"👇 {bold('Чем займемся сегодня?')}"
            
            await safe_send_message(user_id, text)
            logger.info(f"✅ Утреннее сообщение отправлено пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке утреннего сообщения: {e}")
    
    def schedule_reminder(self, user_id: int, reminder_type: str, delay_minutes: int):
        """Планирует напоминание"""
        # TODO: реализовать планирование напоминаний
        pass

# Глобальный экземпляр планировщика
scheduler = TaskScheduler()
