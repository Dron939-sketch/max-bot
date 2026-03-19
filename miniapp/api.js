# Добавь в main.py после существующих эндпоинтов

@api_app.get("/api/chat/history")
async def get_chat_history(user_id: int, limit: int = 50):
    """Возвращает историю чата пользователя"""
    try:
        # Здесь можно получать из БД, если сохраняете историю
        # Или генерировать на основе последних действий
        
        # Для начала вернем пустую историю
        return JSONResponse({
            "success": True,
            "history": []
        })
    except Exception as e:
        logger.error(f"❌ Error in get_chat_history: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.post("/api/chat/message")
async def chat_message(request: Request):
    """Отправляет сообщение боту и получает ответ"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        message = data.get('message')
        mode = data.get('mode')
        
        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message required")
        
        # Получаем контекст пользователя
        context = user_contexts.get(user_id)
        if not context:
            context = UserContext(user_id)
            user_contexts[user_id] = context
        
        # Устанавливаем режим, если передан
        if mode and mode in COMMUNICATION_MODES:
            context.communication_mode = mode
        
        # Генерируем ответ через DeepSeek
        from services import call_deepseek_with_context
        response = await call_deepseek_with_context(
            user_id=user_id,
            user_message=message,
            context=context,
            mode=context.communication_mode,
            profile_data=user_data.get(user_id, {})
        )
        
        return JSONResponse({
            "success": True,
            "response": response,
            "mode": context.communication_mode
        })
        
    except Exception as e:
        logger.error(f"❌ Error in chat_message: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False, 
                "error": str(e),
                "response": "Произошла ошибка. Попробуйте еще раз."
            }
        )

@api_app.post("/api/chat/action")
async def chat_action(request: Request):
    """Обрабатывает нажатия на кнопки"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        action = data.get('action')
        action_data = data.get('data', {})
        
        if not user_id or not action:
            raise HTTPException(status_code=400, detail="user_id and action required")
        
        # Обрабатываем действия
        if action == "start_test":
            return JSONResponse({
                "success": True,
                "action": action,
                "data": {"stage": 1, "question_index": 0}
            })
        elif action == "show_profile":
            profile_data = await get_profile(user_id)
            return JSONResponse({
                "success": True,
                "action": action,
                "data": profile_data
            })
        
        return JSONResponse({"success": True, "action": action})
        
    except Exception as e:
        logger.error(f"❌ Error in chat_action: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.get("/api/test/question")
async def get_test_question(user_id: int, stage: int, index: int):
    """Возвращает вопрос теста"""
    try:
        # Здесь логика получения вопроса из БД
        # Можно использовать существующие функции из handlers/questions.py
        
        return JSONResponse({
            "success": True,
            "stage": stage,
            "index": index,
            "total": 4,  # Замени на реальное количество
            "text": "Вопрос теста",
            "options": [
                {"id": "A", "text": "Вариант А", "value": "A"},
                {"id": "B", "text": "Вариант Б", "value": "B"},
                {"id": "C", "text": "Вариант В", "value": "C"},
                {"id": "D", "text": "Вариант Г", "value": "D"}
            ],
            "hasAnswer": False
        })
    except Exception as e:
        logger.error(f"❌ Error in get_test_question: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@api_app.post("/api/test/answer")
async def submit_test_answer(request: Request):
    """Сохраняет ответ на вопрос теста"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        stage = data.get('stage')
        question_index = data.get('question_index')
        answer = data.get('answer')
        option = data.get('option')
        
        # Сохраняем ответ в user_data
        if user_id not in user_data:
            user_data[user_id] = {}
        
        if 'all_answers' not in user_data[user_id]:
            user_data[user_id]['all_answers'] = []
        
        user_data[user_id]['all_answers'].append({
            'stage': stage,
            'question_index': question_index,
            'answer': answer,
            'option': option,
            'timestamp': datetime.now().isoformat()
        })
        
        # Сохраняем в БД
        asyncio.create_task(save_user_to_db(user_id, user_data, user_contexts, user_routes))
        
        # Проверяем, завершен ли этап
        stage_complete = False  # Здесь логика проверки
        
        return JSONResponse({
            "success": True,
            "stageComplete": stage_complete
        })
    except Exception as e:
        logger.error(f"❌ Error in submit_test_answer: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
