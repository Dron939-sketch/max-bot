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
from formatters import bold  # 👈 ДОБАВЛЕНО

logger = logging.getLogger(__name__)

class TaskScheduler:
    """Планировщик периодических задач"""
    
    def __init__(self):
        self.tasks = {}
        self.running = False
        self.morning_sent_today = set()  # 👈 ДОБАВЛЕНО: чтобы не отправлять дважды
        self.last_check_date = None  # 👈 ДОБАВЛЕНО
    
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
            
            # Обновляем дату для сброса morning_sent_today
            if self.last_check_date != now.date():
                self.last_check_date = now.date()
                self.morning_sent_today.clear()
                logger.info(f"📅 Новая дата: {now.date()}, сброс утренних отправок")
            
            # Проверяем задачи каждый час
            if now.minute == 0:
                await self._check_morning_messages()
                await self._check_reminders()  # 👈 ДОБАВЛЕНО
            
            await asyncio.sleep(60)  # Проверка каждую минуту
    
    async def _check_morning_messages(self):
        """Проверяет и отправляет утренние сообщения"""
        now = datetime.now()
        
        # Отправляем в 9:00 утра
        if now.hour == 9:
            for user_id, context in user_contexts.items():
                # Проверяем, есть ли профиль у пользователя
                user_data_dict = user_data.get(user_id, {})
                has_profile = user_data_dict.get("profile_data") or user_data_dict.get("ai_generated_profile")
                
                # Отправляем только если есть профиль и еще не отправляли сегодня
                if has_profile and context and user_id not in self.morning_sent_today:
                    await self._send_morning_message(user_id)
                    self.morning_sent_today.add(user_id)
    
    async def _send_morning_message(self, user_id: int):
        """Отправляет утреннее сообщение пользователю"""
        try:
            context = user_contexts.get(user_id)
            if not context:
                logger.warning(f"Нет контекста для пользователя {user_id}")
                return
            
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
    
    async def _check_reminders(self):
        """Проверяет запланированные напоминания"""
        now = datetime.now()
        to_remove = []
        
        for user_id, reminder in self.tasks.items():
            if reminder.get('time') <= now:
                await self._send_reminder(user_id, reminder)
                to_remove.append(user_id)
        
        # Удаляем отправленные напоминания
        for user_id in to_remove:
            del self.tasks[user_id]
    
    async def _send_reminder(self, user_id: int, reminder: Dict):
        """Отправляет напоминание пользователю"""
        try:
            reminder_type = reminder.get('type', 'general')
            message = reminder.get('message', 'Напоминание')
            
            text = f"⏰ {bold('НАПОМИНАНИЕ')}\n\n{message}"
            
            await safe_send_message(user_id, text)
            logger.info(f"✅ Напоминание отправлено пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания: {e}")
    
    def schedule_reminder(self, user_id: int, reminder_type: str, delay_minutes: int, message: str = None):
        """
        Планирует напоминание
        
        Args:
            user_id: ID пользователя
            reminder_type: тип напоминания ('checkin', 'task', 'motivation')
            delay_minutes: через сколько минут отправить
            message: текст напоминания (если None, генерируется по типу)
        """
        reminder_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        if not message:
            messages = {
                'checkin': "Как дела? Что сделано за сегодня?",
                'task': "Не забудь про задачу!",
                'motivation': "Ты сможешь! Продолжай двигаться к цели 💪"
            }
            message = messages.get(reminder_type, "Напоминание")
        
        self.tasks[user_id] = {
            'time': reminder_time,
            'type': reminder_type,
            'message': message,
            'created': datetime.now()
        }
        
        logger.info(f"✅ Напоминание запланировано для пользователя {user_id} на {reminder_time}")
        return True
    
    def cancel_user_reminders(self, user_id: int):
        """Отменяет все напоминания для пользователя"""
        if user_id in self.tasks:
            del self.tasks[user_id]
            logger.info(f"✅ Напоминания для пользователя {user_id} отменены")
            return True
        return False
    
    def get_user_reminders(self, user_id: int) -> List[Dict]:
        """Возвращает список напоминаний для пользователя"""
        if user_id in self.tasks:
            return [self.tasks[user_id]]
        return []
    
    def stop(self):
        """Останавливает планировщик"""
        self.running = False
        logger.info("🛑 Планировщик задач остановлен")

# Глобальный экземпляр планировщика
scheduler = TaskScheduler()
