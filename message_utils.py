"""
Утилиты для отправки сообщений в MAX
"""
import logging
import time
from maxibot import types
from maxibot.api import MAXBotAPI

# Предполагаем, что экземпляр бота будет передан или доступен глобально
# Лучше сделать так, чтобы функции принимали bot как параметр
from bot_instance import bot  # или откуда вы импортируете bot

from formatters import clean_text_for_safe_display

logger = logging.getLogger(__name__)


def safe_send_message(
    message: types.Message, 
    text: str, 
    reply_markup=None, 
    parse_mode: str = 'HTML', 
    delete_previous: bool = True
) -> types.Message:
    """Безопасно отправляет сообщение с HTML-разметкой и удаляет предыдущее"""
    
    chat_id = message.chat.id
    
    # Удаляем предыдущее сообщение бота, если оно было
    if delete_previous and hasattr(message, 'message_id'):
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception as e:
            if "message can't be deleted" not in str(e).lower():
                logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Отправляем новое сообщение
    try:
        return bot.send_message(
            chat_id, 
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
    except Exception as e:
        if "can't parse entities" in str(e).lower() or "parse" in str(e).lower():
            # Если ошибка парсинга, отправляем без форматирования
            clean_text = clean_text_for_safe_display(text)
            logger.warning(f"Ошибка парсинга HTML, отправляем без форматирования: {e}")
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
        # Если другая ошибка - пробрасываем дальше
        raise


def send_with_status_cleanup(
    message: types.Message, 
    text: str, 
    status_msg: types.Message = None, 
    reply_markup=None, 
    parse_mode: str = 'HTML'
) -> types.Message:
    """Отправляет сообщение и удаляет статусное сообщение"""
    
    chat_id = message.chat.id
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except Exception as e:
            logger.debug(f"Не удалось удалить статусное сообщение: {e}")
    
    # Удаляем предыдущее сообщение пользователя/бота
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        logger.debug(f"Не удалось удалить исходное сообщение: {e}")
    
    # Отправляем новое сообщение
    try:
        return bot.send_message(
            chat_id, 
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
    except Exception as e:
        if "can't parse entities" in str(e).lower() or "parse" in str(e).lower():
            clean_text = clean_text_for_safe_display(text)
            logger.warning(f"Ошибка парсинга HTML, отправляем без форматирования: {e}")
            return bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
        raise


# Дополнительная полезная функция для MAX
def safe_edit_message(
    message: types.Message, 
    new_text: str, 
    reply_markup=None, 
    parse_mode: str = 'HTML'
) -> types.Message:
    """Безопасно редактирует существующее сообщение"""
    try:
        return bot.edit_message_text(
            new_text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        if "message is not modified" in str(e).lower():
            # Сообщение не изменилось - это не ошибка
            return message
        elif "can't parse entities" in str(e).lower():
            clean_text = clean_text_for_safe_display(new_text)
            return bot.edit_message_text(
                clean_text,
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=reply_markup
            )
        raise
