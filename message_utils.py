#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для отправки сообщений в MAX
"""
import logging
from maxibot import types
from maxibot import MaxiBot  # вместо MAXBotAPI

# Импортируем бота (убедись, что bot_instance.py существует)
from bot_instance import bot

from formatters import clean_text_for_safe_display

logger = logging.getLogger(__name__)


def safe_send_message(
    message: types.Message, 
    text: str, 
    reply_markup=None, 
    parse_mode: str = 'HTML', 
    delete_previous: bool = True
) -> types.Message:
    """
    Безопасно отправляет сообщение с HTML-разметкой и удаляет предыдущее
    
    Аргументы:
        message: сообщение пользователя (содержит chat.id)
        text: текст для отправки
        reply_markup: клавиатура (опционально)
        parse_mode: режим форматирования (HTML по умолчанию)
        delete_previous: удалять ли предыдущее сообщение
    
    Возвращает:
        отправленное сообщение
    """
    chat_id = message.chat.id
    
    # Удаляем предыдущее сообщение бота, если оно было
    if delete_previous and hasattr(message, 'message_id'):
        try:
            bot.delete_message(chat_id, message.message_id)
            logger.debug(f"Удалено сообщение {message.message_id}")
        except Exception as e:
            if "message can't be deleted" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Отправляем новое сообщение
    try:
        sent_msg = bot.send_message(
            chat_id, 
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
        logger.debug(f"Отправлено сообщение {sent_msg.message_id}")
        return sent_msg
    except Exception as e:
        if "can't parse entities" in str(e).lower() or "parse" in str(e).lower():
            # Если ошибка парсинга, отправляем без форматирования
            clean_text = clean_text_for_safe_display(text)
            logger.warning(f"Ошибка парсинга HTML, отправляем без форматирования: {e}")
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
        # Если другая ошибка - пробрасываем дальше
        logger.error(f"Критическая ошибка при отправке: {e}")
        raise


def send_with_status_cleanup(
    message: types.Message, 
    text: str, 
    status_msg: types.Message = None, 
    reply_markup=None, 
    parse_mode: str = 'HTML'
) -> types.Message:
    """
    Отправляет сообщение и удаляет статусное сообщение
    
    Аргументы:
        message: сообщение пользователя
        text: текст для отправки
        status_msg: статусное сообщение для удаления
        reply_markup: клавиатура
        parse_mode: режим форматирования
    
    Возвращает:
        отправленное сообщение
    """
    chat_id = message.chat.id
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
            logger.debug(f"Удалено статусное сообщение {status_msg.message_id}")
        except Exception as e:
            logger.debug(f"Не удалось удалить статусное сообщение: {e}")
    
    # Удаляем предыдущее сообщение пользователя/бота
    try:
        bot.delete_message(chat_id, message.message_id)
        logger.debug(f"Удалено исходное сообщение {message.message_id}")
    except Exception as e:
        logger.debug(f"Не удалось удалить исходное сообщение: {e}")
    
    # Отправляем новое сообщение
    try:
        sent_msg = bot.send_message(
            chat_id, 
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
        logger.debug(f"Отправлено новое сообщение {sent_msg.message_id}")
        return sent_msg
    except Exception as e:
        if "can't parse entities" in str(e).lower() or "parse" in str(e).lower():
            clean_text = clean_text_for_safe_display(text)
            logger.warning(f"Ошибка парсинга HTML, отправляем без форматирования: {e}")
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
        logger.error(f"Критическая ошибка при отправке: {e}")
        raise


def safe_edit_message(
    message: types.Message, 
    new_text: str, 
    reply_markup=None, 
    parse_mode: str = 'HTML'
) -> types.Message:
    """
    Безопасно редактирует существующее сообщение
    
    Аргументы:
        message: сообщение для редактирования
        new_text: новый текст
        reply_markup: новая клавиатура (или None)
        parse_mode: режим форматирования
    
    Возвращает:
        отредактированное сообщение
    """
    try:
        edited_msg = bot.edit_message_text(
            new_text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        logger.debug(f"Отредактировано сообщение {message.message_id}")
        return edited_msg
    except Exception as e:
        error_str = str(e).lower()
        
        if "message is not modified" in error_str:
            # Сообщение не изменилось - это не ошибка
            logger.debug("Сообщение не изменилось, пропускаем")
            return message
            
        elif "can't parse entities" in error_str:
            clean_text = clean_text_for_safe_display(new_text)
            logger.warning(f"Ошибка парсинга HTML при редактировании: {e}")
            return bot.edit_message_text(
                clean_text,
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=reply_markup
            )
        
        logger.error(f"Критическая ошибка при редактировании: {e}")
        raise


# ============================================
# ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ ДЛЯ MAX
# ============================================

def safe_send_typing(chat_id: int):
    """
    Отправляет индикатор "печатает" (если поддерживается MAX)
    
    Аргументы:
        chat_id: ID чата
    """
    try:
        # Проверяем, есть ли такой метод в MAX API
        if hasattr(bot, 'send_chat_action'):
            bot.send_chat_action(chat_id, 'typing')
            logger.debug(f"Отправлен статус 'печатает' в чат {chat_id}")
    except Exception as e:
        logger.debug(f"Не удалось отправить статус печати: {e}")


def safe_delete_message(chat_id: int, message_id: int) -> bool:
    """
    Безопасно удаляет сообщение по ID
    
    Аргументы:
        chat_id: ID чата
        message_id: ID сообщения
    
    Возвращает:
        True если удалено, False если нет
    """
    try:
        bot.delete_message(chat_id, message_id)
        logger.debug(f"Удалено сообщение {message_id}")
        return True
    except Exception as e:
        if "message can't be deleted" not in str(e).lower():
            logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")
        return False
