#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для отправки сообщений в MAX
Исправленная версия с поддержкой длинных сообщений и безопасной отправкой
"""

import logging
import re
import time
from typing import Optional, Union, List, Dict, Any

from maxibot import types
from maxibot import MaxiBot

# Импортируем бота (убедись, что bot_instance.py существует)
from bot_instance import bot

from formatters import clean_text_for_safe_display

logger = logging.getLogger(__name__)

# Хранилище последних сообщений для каждого пользователя
# Структура: {chat_id: [message_id1, message_id2, ...]}
user_messages_history: Dict[int, List[int]] = {}

# Максимальное количество сообщений для хранения истории на пользователя
MAX_HISTORY_PER_USER = 10

# Максимальная длина сообщения (лимит Telegram)
MAX_MESSAGE_LENGTH = 4096


def safe_send_message(
    message: Optional[Union[types.Message, int]],
    text: str,
    reply_markup: Any = None,
    parse_mode: str = 'HTML',
    delete_previous: bool = False,
    keep_last: int = 1,
    silent: bool = False,
    chat_id: Optional[int] = None,
    **kwargs
) -> Optional[types.Message]:
    """
    Безопасно отправляет сообщение с опцией удаления предыдущих
    
    Args:
        message: исходное сообщение или chat_id (может быть None)
        text: текст для отправки
        reply_markup: клавиатура (опционально)
        parse_mode: режим форматирования
        delete_previous: удалить ли предыдущие сообщения бота
        keep_last: сколько последних сообщений оставлять
        silent: не логировать успешные отправки
        chat_id: ID чата (если message=None)
        **kwargs: дополнительные параметры для send_message
    
    Returns:
        отправленное сообщение или None при ошибке
    """
    # Проверяем текст
    if not text:
        logger.error("❌ Попытка отправить пустое сообщение")
        return None
    
    # Проверяем длину текста
    if len(text) > MAX_MESSAGE_LENGTH:
        logger.error(f"❌ Длина текста {len(text)} превышает лимит {MAX_MESSAGE_LENGTH}")
        # Обрезаем до безопасной длины
        text = text[:MAX_MESSAGE_LENGTH - 3] + "..."
        logger.info(f"✂️ Текст обрезан до {MAX_MESSAGE_LENGTH} символов")
    
    # Получаем chat_id
    cid = None
    if chat_id:
        cid = chat_id
    elif message is not None:
        if isinstance(message, int):
            cid = message
        elif hasattr(message, 'chat') and hasattr(message.chat, 'id'):
            cid = message.chat.id
        elif hasattr(message, 'chat_id'):
            cid = message.chat_id
    
    if cid is None:
        logger.error("❌ Не удалось определить chat_id")
        return None
    
    try:
        # Если нужно удалить предыдущие сообщения
        if delete_previous and cid in user_messages_history:
            # Получаем список сообщений для удаления (все кроме keep_last последних)
            history = user_messages_history.get(cid, [])
            if len(history) > keep_last:
                messages_to_delete = history[:-keep_last] if keep_last > 0 else history
                
                for msg_id in messages_to_delete:
                    try:
                        bot.delete_message(cid, msg_id)
                        if not silent:
                            logger.debug(f"🗑️ Удалено сообщение {msg_id} для чата {cid}")
                        # Небольшая пауза чтобы не превысить лимиты
                        time.sleep(0.05)
                    except Exception as e:
                        # Игнорируем ошибки удаления (сообщение могло быть уже удалено)
                        pass
                
                # Оставляем только последние keep_last сообщений
                user_messages_history[cid] = history[-keep_last:] if keep_last > 0 else []
        
        # Отправляем новое сообщение
        send_kwargs = {
            'chat_id': cid,
            'text': text,
            'parse_mode': parse_mode
        }
        
        if reply_markup is not None:
            send_kwargs['reply_markup'] = reply_markup
        
        # Добавляем дополнительные параметры из kwargs
        send_kwargs.update(kwargs)
        
        sent_msg = bot.send_message(**send_kwargs)
        
        # Сохраняем в историю
        if cid not in user_messages_history:
            user_messages_history[cid] = []
        
        user_messages_history[cid].append(sent_msg.message_id)
        
        # Ограничиваем размер истории
        if len(user_messages_history[cid]) > MAX_HISTORY_PER_USER:
            user_messages_history[cid] = user_messages_history[cid][-MAX_HISTORY_PER_USER:]
        
        if not silent:
            logger.debug(f"📤 Отправлено сообщение {sent_msg.message_id} в чат {cid}")
        
        return sent_msg
        
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ Ошибка при отправке сообщения: {e}")
        
        # Пробуем отправить без форматирования
        try:
            clean_text = re.sub(r'<[^>]+>', '', text)
            if len(clean_text) > MAX_MESSAGE_LENGTH:
                clean_text = clean_text[:MAX_MESSAGE_LENGTH - 3] + "..."
            
            sent_msg = bot.send_message(
                chat_id=cid,
                text=clean_text,
                reply_markup=reply_markup
            )
            
            # Сохраняем в историю
            if cid not in user_messages_history:
                user_messages_history[cid] = []
            user_messages_history[cid].append(sent_msg.message_id)
            
            logger.warning(f"⚠️ Сообщение отправлено без форматирования в чат {cid}")
            return sent_msg
            
        except Exception as e2:
            logger.error(f"❌ Критическая ошибка при отправке: {e2}")
            return None


def send_with_status_cleanup(
    message: types.Message, 
    text: str, 
    status_msg: Optional[types.Message] = None, 
    reply_markup: Any = None, 
    parse_mode: str = 'HTML',
    keep_last: int = 1
) -> Optional[types.Message]:
    """
    Отправляет сообщение и удаляет статусное сообщение и предыдущее сообщение пользователя
    
    Args:
        message: сообщение пользователя
        text: текст для отправки
        status_msg: статусное сообщение для удаления
        reply_markup: клавиатура
        parse_mode: режим форматирования
        keep_last: сколько последних сообщений оставлять
    
    Returns:
        отправленное сообщение
    """
    chat_id = message.chat.id
    
    # Проверяем длину текста
    if len(text) > MAX_MESSAGE_LENGTH:
        logger.warning(f"⚠️ Текст слишком длинный: {len(text)} > {MAX_MESSAGE_LENGTH}")
        # Разбиваем на части и отправляем первую часть
        from handlers.profile import split_long_message
        parts = split_long_message(text, MAX_MESSAGE_LENGTH - 100)
        text = parts[0] + f"\n\n<code>✉️ Часть 1/{len(parts)}</code>"
    
    # Удаляем статусное сообщение, если оно есть
    if status_msg:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
            logger.debug(f"🗑️ Удалено статусное сообщение {status_msg.message_id}")
        except Exception as e:
            logger.debug(f"Не удалось удалить статусное сообщение: {e}")
    
    # Удаляем предыдущее сообщение пользователя/бота
    try:
        bot.delete_message(chat_id, message.message_id)
        logger.debug(f"🗑️ Удалено исходное сообщение {message.message_id}")
    except Exception as e:
        logger.debug(f"Не удалось удалить исходное сообщение: {e}")
    
    # Удаляем предыдущие сообщения из истории
    if chat_id in user_messages_history:
        history = user_messages_history.get(chat_id, [])
        if len(history) > keep_last:
            messages_to_delete = history[:-keep_last] if keep_last > 0 else history
            
            for msg_id in messages_to_delete:
                try:
                    bot.delete_message(chat_id, msg_id)
                    logger.debug(f"🗑️ Удалено сообщение из истории {msg_id}")
                    time.sleep(0.05)
                except:
                    pass
            
            user_messages_history[chat_id] = history[-keep_last:] if keep_last > 0 else []
    
    # Отправляем новое сообщение
    try:
        sent_msg = bot.send_message(
            chat_id, 
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
        logger.debug(f"📤 Отправлено новое сообщение {sent_msg.message_id}")
        
        # Сохраняем в историю
        if chat_id not in user_messages_history:
            user_messages_history[chat_id] = []
        user_messages_history[chat_id].append(sent_msg.message_id)
        
        return sent_msg
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "can't parse entities" in error_msg or "parse" in error_msg:
            clean_text = clean_text_for_safe_display(text)
            logger.warning(f"⚠️ Ошибка парсинга HTML, отправляем без форматирования: {e}")
            
            try:
                sent_msg = bot.send_message(chat_id, clean_text, reply_markup=reply_markup)
                
                # Сохраняем в историю
                if chat_id not in user_messages_history:
                    user_messages_history[chat_id] = []
                user_messages_history[chat_id].append(sent_msg.message_id)
                
                return sent_msg
            except Exception as e2:
                logger.error(f"❌ Ошибка при отправке без форматирования: {e2}")
                return None
        else:
            logger.error(f"❌ Критическая ошибка при отправке: {e}")
            return None


def safe_edit_message(
    message: types.Message, 
    new_text: str, 
    reply_markup: Any = None, 
    parse_mode: str = 'HTML'
) -> Optional[types.Message]:
    """
    Безопасно редактирует существующее сообщение
    
    Args:
        message: сообщение для редактирования
        new_text: новый текст
        reply_markup: новая клавиатура (или None)
        parse_mode: режим форматирования
    
    Returns:
        отредактированное сообщение или None при ошибке
    """
    # Проверяем длину текста
    if len(new_text) > MAX_MESSAGE_LENGTH:
        logger.warning(f"⚠️ Текст для редактирования слишком длинный: {len(new_text)} > {MAX_MESSAGE_LENGTH}")
        new_text = new_text[:MAX_MESSAGE_LENGTH - 3] + "..."
    
    try:
        edited_msg = bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=new_text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        logger.debug(f"✏️ Отредактировано сообщение {message.message_id}")
        return edited_msg
        
    except Exception as e:
        error_str = str(e).lower()
        
        if "message is not modified" in error_str:
            # Сообщение не изменилось - это не ошибка
            logger.debug("Сообщение не изменилось, пропускаем")
            return message
            
        elif "can't parse entities" in error_str:
            clean_text = clean_text_for_safe_display(new_text)
            logger.warning(f"⚠️ Ошибка парсинга HTML при редактировании: {e}")
            
            try:
                return bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    text=clean_text,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"❌ Ошибка при повторном редактировании: {e2}")
                return None
        
        elif "message to edit not found" in error_str:
            logger.error(f"❌ Сообщение {message.message_id} не найдено для редактирования")
            return None
        
        logger.error(f"❌ Критическая ошибка при редактировании: {e}")
        return None


# ============================================
# ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ
# ============================================

def safe_send_typing(chat_id: int):
    """
    Отправляет индикатор "печатает" (если поддерживается MAX)
    
    Args:
        chat_id: ID чата
    """
    try:
        # Проверяем, есть ли такой метод в MAX API
        if hasattr(bot, 'send_chat_action'):
            bot.send_chat_action(chat_id, 'typing')
            logger.debug(f"✏️ Отправлен статус 'печатает' в чат {chat_id}")
    except Exception as e:
        logger.debug(f"Не удалось отправить статус печати: {e}")


def safe_delete_message(chat_id: int, message_id: int) -> bool:
    """
    Безопасно удаляет сообщение по ID
    
    Args:
        chat_id: ID чата
        message_id: ID сообщения
    
    Returns:
        True если удалено, False если нет
    """
    try:
        bot.delete_message(chat_id, message_id)
        logger.debug(f"🗑️ Удалено сообщение {message_id}")
        
        # Удаляем из истории
        if chat_id in user_messages_history:
            if message_id in user_messages_history[chat_id]:
                user_messages_history[chat_id].remove(message_id)
        
        return True
        
    except Exception as e:
        error_msg = str(e).lower()
        if "message can't be deleted" not in error_msg and "message to delete not found" not in error_msg:
            logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")
        return False


def clear_user_history(chat_id: int, keep_last: int = 0):
    """
    Очищает всю историю сообщений пользователя
    
    Args:
        chat_id: ID чата
        keep_last: сколько последних сообщений оставить
    """
    if chat_id not in user_messages_history:
        return
    
    history = user_messages_history.get(chat_id, [])
    
    if keep_last > 0 and len(history) > keep_last:
        messages_to_delete = history[:-keep_last]
        history = history[-keep_last:]
    else:
        messages_to_delete = history
        history = []
    
    for msg_id in messages_to_delete:
        try:
            bot.delete_message(chat_id, msg_id)
            logger.debug(f"🗑️ Удалено сообщение {msg_id} при очистке истории")
            time.sleep(0.05)
        except:
            pass
    
    user_messages_history[chat_id] = history
    logger.info(f"🧹 Очищена история для чата {chat_id}, оставлено {len(history)} сообщений")


def get_user_history(chat_id: int) -> List[int]:
    """Возвращает историю сообщений пользователя"""
    return user_messages_history.get(chat_id, [])


def split_and_send_long_message(
    message: Union[types.Message, int],
    text: str,
    reply_markup: Any = None,
    parse_mode: str = 'HTML',
    delete_previous: bool = False,
    keep_last: int = 1,
    max_length: int = 3500
) -> List[Optional[types.Message]]:
    """
    Разбивает длинное сообщение на части и отправляет их
    
    Args:
        message: исходное сообщение или chat_id
        text: длинный текст
        reply_markup: клавиатура (будет прикреплена только к последней части)
        parse_mode: режим форматирования
        delete_previous: удалять ли предыдущие сообщения
        keep_last: сколько последних сообщений оставлять
        max_length: максимальная длина одной части
    
    Returns:
        список отправленных сообщений
    """
    from handlers.profile import split_long_message
    
    parts = split_long_message(text, max_length)
    sent_messages = []
    
    for i, part in enumerate(parts):
        # Добавляем индикатор части для всех, кроме последней
        if i < len(parts) - 1:
            part_text = f"{part}\n\n<code>✉️ Часть {i+1}/{len(parts)}</code>"
            current_markup = None
        else:
            part_text = part
            current_markup = reply_markup
        
        # Для последней части добавляем "Что дальше?" если нужно
        if i == len(parts) - 1 and "👇" not in part_text:
            part_text = f"{part_text}\n\n👇 <b>Что дальше?</b>"
        
        # Отправляем часть
        sent = safe_send_message(
            message,
            part_text,
            reply_markup=current_markup,
            parse_mode=parse_mode,
            delete_previous=(i == 0 and delete_previous),  # Удаляем предыдущие только для первой части
            keep_last=keep_last,
            silent=True
        )
        
        if sent:
            sent_messages.append(sent)
        
        # Пауза между отправками
        if i < len(parts) - 1:
            time.sleep(0.5)
    
    logger.info(f"📨 Отправлено {len(sent_messages)}/{len(parts)} частей сообщения")
    return sent_messages
