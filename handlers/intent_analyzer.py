def process_text_question_sync(
    message: Message, 
    user_id: int, 
    text: str, 
    show_question_text: bool = True
):
    """
    СИНХРОННАЯ обработка текстового сообщения пользователя
    С ИСПОЛЬЗОВАНИЕМ ОТДЕЛЬНОГО АНАЛИЗАТОРА НАМЕРЕНИЙ
    """
    if is_processing(user_id):
        logger.warning(f"⚠️ Запрос от пользователя {user_id} уже обрабатывается, пропускаем")
        safe_send_message(
            message,
            "⏳ Ваш предыдущий вопрос еще обрабатывается. Пожалуйста, подождите...",
            delete_previous=True
        )
        return
    
    set_processing(user_id, True)
    
    try:
        user_data_dict = get_user_data_dict(user_id)
        
        if not is_test_completed_check(user_data_dict):
            safe_send_message(
                message,
                "❓ Сначала нужно пройти тест. Используйте /start",
                delete_previous=True
            )
            return
        
        status_msg = safe_send_message(
            message,
            "🎙 Думаю над ответом...",
            delete_previous=True
        )
        
        context_obj = get_user_context_obj(user_id)
        mode_name = context_obj.communication_mode if context_obj else "coach"
        mode_config = COMMUNICATION_MODES.get(mode_name, COMMUNICATION_MODES["coach"])
        user_name = get_user_name(user_id)
        
        # Формируем информацию о профиле
        profile_data = user_data_dict.get('profile_data', {})
        profile_info = f"""
- Имя: {user_name}
- Профиль: {profile_data.get('display_name', 'не определен')}
- Тип восприятия: {user_data_dict.get('perception_type', 'не определен')}
- Уровень мышления: {user_data_dict.get('thinking_level', 5)}/9
"""
        
        # ============================================
        # ШАГ 1: АНАЛИЗ НАМЕРЕНИЯ (в отдельном потоке)
        # ============================================
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            intent_data = loop.run_until_complete(intent_analyzer.analyze(text))
        finally:
            loop.close()
        
        intent = intent_data.get("intent", "QUESTION")
        confidence = intent_data.get("confidence", 0.7)
        
        logger.info(f"🔍 Анализ намерения: intent={intent}, confidence={confidence}")
        
        # ============================================
        # ШАГ 2: ГЕНЕРАЦИЯ ОТВЕТА
        # ============================================
        
        # Формируем промпт для ответа
        response_prompt = intent_analyzer.get_response_prompt(
            intent_data=intent_data,
            text=text,
            user_name=user_name,
            profile_info=profile_info,
            mode_config=mode_config
        )
        
        logger.info(f"📝 Генерация ответа для intent={intent}")
        
        # Генерируем ответ
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(call_deepseek(response_prompt, max_tokens=1000))
        finally:
            loop.close()
        
        if not response:
            response = intent_analyzer.get_fallback_response(intent, user_name)
        
        # Логируем ответ
        logger.info(f"💬 ОТВЕТ ({len(response)} символов): {response[:200]}...")
        
        # Сохраняем в историю
        history = user_data_dict.get('history', [])
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": response})
        user_data_dict["history"] = history
        
        sync_db.save_user_to_db(user_id)
        
        clean_response = clean_text_for_safe_display(response)
        
        # Клавиатура
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("🎤 ЗАДАТЬ ЕЩЁ", callback_data="ask_question"),
            InlineKeyboardButton("🎯 К ЦЕЛИ", callback_data="show_dynamic_destinations")
        )
        keyboard.row(InlineKeyboardButton("🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought"))
        keyboard.row(InlineKeyboardButton("◀️ К ПОРТРЕТУ", callback_data="show_results"))
        
        # Удаляем статусное сообщение
        if status_msg:
            try:
                safe_delete_message(message.chat.id, status_msg.message_id)
            except Exception:
                pass
        
        # Показываем вопрос (если нужно)
        if show_question_text:
            safe_send_message(
                message,
                f"📝 **Вы сказали:**\n{text}",
                delete_previous=False
            )
        
        # Отправляем ответ
        safe_send_message(
            message,
            f"💭 **Ответ**\n\n{clean_response}",
            reply_markup=keyboard,
            parse_mode=None,
            delete_previous=not show_question_text
        )
        
        # Генерируем голос
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                voice_text = response[:5000] if len(response) > 5000 else response
                audio_data = loop.run_until_complete(text_to_speech(voice_text, mode_name))
                if audio_data:
                    success = loop.run_until_complete(send_voice_to_max(message.chat.id, audio_data))
                    if success:
                        logger.info(f"🎙 Голосовой ответ отправлен пользователю {user_id}")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке голоса: {e}")
        
        # Оставляем состояние для следующих вопросов
        set_state(user_id, TestStates.awaiting_question)
        
    finally:
        set_processing(user_id, False)
