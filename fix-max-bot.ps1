# fix-max-bot.ps1
# Скрипт для автоматического исправления проблемы с контекстом в MAX боте

Write-Host "🔧 Автоматическое исправление MAX бота" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Параметры подключения к Render
$serviceId = "srv-d6s1tg7diees73c45rag"
$apiKey = Read-Host "Введите ваш API ключ Render (rnd_...)"

if (-not $apiKey) {
    Write-Host "❌ API ключ не введен!" -ForegroundColor Red
    exit
}

$headers = @{
    "Authorization" = "Bearer $apiKey"
    "Content-Type" = "application/json"
}

Write-Host "✅ Подключение к Render API..." -ForegroundColor Green

# ============================================
# ШАГ 1: Получаем список файлов
# ============================================
Write-Host "`n📁 Шаг 1: Получаем список файлов..." -ForegroundColor Yellow

try {
    $filesUrl = "https://api.render.com/v1/services/$serviceId/files"
    $files = Invoke-RestMethod -Uri $filesUrl -Headers $headers
    Write-Host "✅ Найдено файлов: $($files.Count)" -ForegroundColor Green
} catch {
    Write-Host "❌ Ошибка получения списка файлов: $_" -ForegroundColor Red
    exit
}

# ============================================
# ШАГ 2: Скачиваем handlers/context.py
# ============================================
Write-Host "`n📥 Шаг 2: Скачиваем handlers/context.py..." -ForegroundColor Yellow

$contextUrl = "https://api.render.com/v1/services/$serviceId/files/handlers/context.py"
try {
    $contextContent = Invoke-RestMethod -Uri $contextUrl -Headers $headers
    Write-Host "✅ Файл скачан!" -ForegroundColor Green
} catch {
    Write-Host "❌ Ошибка скачивания: $_" -ForegroundColor Red
    exit
}

# ============================================
# ШАГ 3: Исправляем файл
# ============================================
Write-Host "`n🔧 Шаг 3: Исправляем файл..." -ForegroundColor Yellow

# Проверяем, есть ли уже наши логи
if ($contextContent -match "handle_context_message вызван") {
    Write-Host "✅ Файл уже содержит логи!" -ForegroundColor Green
} else {
    Write-Host "📝 Добавляем логи в handle_context_message..." -ForegroundColor Yellow
    
    # Добавляем логи в начало функции handle_context_message
    $searchPattern = "def handle_context_message\(message: Message\) -> bool:"
    $replaceWith = @"
def handle_context_message(message: Message) -> bool:
    """
    Обрабатывает ответы на контекстные вопросы
    Возвращает True, если сообщение было обработано как контекстное
    """
    user_id = message.from_user.id
    logger.info(f"📥 handle_context_message вызван для user {user_id}, текст: {message.text}")
    
    context = get_user_context(user_id)
    
    if not context:
        logger.warning(f"❌ Контекст не найден для user {user_id}")
        return False
    
    logger.info(f"📊 context.awaiting_context = {context.awaiting_context}")
    
    if not context.awaiting_context:
        logger.info(f"⏭️ Не ожидается контекст, выходим")
        return False
    
    text = message.text.strip()
    logger.info(f"📝 Обрабатываем текст: '{text}' для поля {context.awaiting_context}")
"@
    
    $contextContent = $contextContent -replace $searchPattern, $replaceWith
    
    # Добавляем логи в обработку города
    $cityPattern = "if context.awaiting_context == `"city`":"
    $cityReplace = @"
if context.awaiting_context == "city":
        # Обработка города
        logger.info(f"🏙️ Сохраняем город: {text}")
"@
    $contextContent = $contextContent -replace $cityPattern, $cityReplace
    
    # Добавляем логи после сохранения города
    $afterCityPattern = "context.city = text.*?context.awaiting_context = None"
    $afterCityReplace = @"
context.city = text
        context.awaiting_context = None
        
        # 👇 СИНХРОННЫЕ ВЫЗОВЫ
        logger.info(f"🌤️ Обновляем погоду...")
        context.update_weather()
        logger.info(f"🌍 Определяем часовой пояс...")
        context.detect_timezone_from_city()
        
        # Получаем следующий вопрос
        logger.info(f"❓ Получаем следующий вопрос от ask_for_context()...")
        question, keyboard = context.ask_for_context()
        logger.info(f"📋 Следующий вопрос: '{question}', клавиатура: {keyboard is not None}")
"@
    $contextContent = $contextContent -replace $afterCityPattern, $afterCityReplace
    
    Write-Host "✅ Логи добавлены!" -ForegroundColor Green
}

# ============================================
# ШАГ 4: Сохраняем исправленный файл локально
# ============================================
Write-Host "`n💾 Шаг 4: Сохраняем локальную копию..." -ForegroundColor Yellow

$localPath = "context_fixed.py"
$contextContent | Out-File -FilePath $localPath -Encoding UTF8
Write-Host "✅ Файл сохранен как $localPath" -ForegroundColor Green

# ============================================
# ШАГ 5: Загружаем обратно на Render
# ============================================
Write-Host "`n📤 Шаг 5: Загружаем исправленный файл..." -ForegroundColor Yellow

$uploadUrl = "https://api.render.com/v1/services/$serviceId/files/handlers/context.py"
$body = $contextContent

try {
    Invoke-RestMethod -Uri $uploadUrl -Method Put -Headers $headers -Body $body
    Write-Host "✅ Файл успешно загружен!" -ForegroundColor Green
} catch {
    Write-Host "❌ Ошибка загрузки: $_" -ForegroundColor Red
    exit
}

# ============================================
# ШАГ 6: Перезапускаем сервис
# ============================================
Write-Host "`n🔄 Шаг 6: Перезапускаем сервис..." -ForegroundColor Yellow

$deployUrl = "https://api.render.com/v1/services/$serviceId/deploys"
$deployBody = @{
    "clearCache" = "do_not_clear"
} | ConvertTo-Json

try {
    Invoke-RestMethod -Uri $deployUrl -Method Post -Headers $headers -Body $deployBody
    Write-Host "✅ Сервис перезапущен!" -ForegroundColor Green
} catch {
    Write-Host "❌ Ошибка перезапуска: $_" -ForegroundColor Red
    exit
}

# ============================================
# ИТОГ
# ============================================
Write-Host "`n" + "="*40 -ForegroundColor Cyan
Write-Host "🎉 ГОТОВО! Все исправления применены!" -ForegroundColor Green
Write-Host "="*40 -ForegroundColor Cyan
Write-Host "`nЧто было сделано:"
Write-Host "✅ Добавлены логи в handle_context_message"
Write-Host "✅ Добавлены логи для отслеживания города"
Write-Host "✅ Файл загружен на Render"
Write-Host "✅ Сервис перезапущен"
Write-Host "`nТеперь проверьте:"
Write-Host "1. Введите город в Telegram"
Write-Host "2. Посмотрите логи на Render Dashboard"
Write-Host "3. Должен появиться следующий вопрос"
Write-Host "`nЛоги можно посмотреть по ссылке:"
Write-Host "https://dashboard.render.com/srv-d6s1tg7diees73c45rag/logs" -ForegroundColor Blue
