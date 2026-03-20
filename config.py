"""
Конфигурация и константы бота для MAX
Ключи API загружаются из переменных окружения (на Render)
ИСПРАВЛЕНО: добавлена проверка MAX_TOKEN для голосовых сообщений
"""
import os
from dotenv import load_dotenv

# Загружаем .env только для локальной разработки
load_dotenv()

# ============================================
# ТОКЕНЫ API (ТОЛЬКО ДЛЯ MAX)
# ============================================

# Токен бота в MAX (получаем у @MasterBot)
MAX_TOKEN = os.environ.get("MAX_TOKEN", "")

# Внешние API (работают одинаково для любой платформы)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY", "")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# ID администраторов
ADMIN_IDS = [532205848]

# ============================================
# URL ВНЕШНИХ API
# ============================================

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"
YANDEX_TTS_API_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


# ============================================
# РЕЖИМЫ ОБЩЕНИЯ
# ============================================

COMMUNICATION_MODES = {
    "coach": {
        "name": "КОУЧ",
        "display_name": "🔮 КОУЧ",
        "emoji": "🔮",
        "voice": "filipp",
        "voice_emotion": "neutral",
        "responsibility": "Помогаю найти ответы внутри вас через открытые вопросы. Не даю готовых решений.",
        "system_prompt": """Ты — КОУЧ. Твоя задача: задавать открытые вопросы, помогать клиенту найти ответы внутри себя.

ТЫ НЕ ДОЛЖЕН:
- Давать готовые советы
- Говорить "я бы на вашем месте"
- Предлагать конкретные решения
- Оценивать и судить

ТЫ ДОЛЖЕН:
- Задавать уточняющие вопросы
- Отражать мысли клиента
- Помогать структурировать размышления
- Поддерживать в поиске собственных ответов

ТВОЯ ФОРМУЛА: вопрос > ответ. Каждый твой ответ должен содержать вопрос.

ГОВОРИ КОРОТКО, ПО ДЕЛУ, БЕЗ ВОДЫ. 2-4 предложения максимум."""
    },
    
    "psychologist": {
        "name": "ПСИХОЛОГ",
        "display_name": "🧠 ПСИХОЛОГ",
        "emoji": "🧠",
        "voice": "ermil",
        "voice_emotion": "good",
        "responsibility": "Анализирую глубинные паттерны, работаю с подсознанием, использую гипнотические техники.",
        "system_prompt": """Ты — ПСИХОЛОГ (интегративный подход: психоанализ + гештальт + эриксоновский гипноз).

Твоя задача — помогать пользователю осознавать глубинные процессы, работать с защитами и паттернами.

ТЫ НЕ ДОЛЖЕН:
- Давать быстрые советы
- Обесценивать переживания
- Торопить с "исцелением"

ТЫ ДОЛЖЕН:
- Создавать безопасное пространство
- Отражать чувства точно
- Исследовать глубинные причины
- Использовать метафоры и образы
- При необходимости - гипнотические техники

ТВОЯ ФОРМУЛА: принятие → исследование → инсайт.

ГОВОРИ: медленно, с паузами, используй образы и метафоры."""
    },
    
    "trainer": {
        "name": "ТРЕНЕР",
        "display_name": "⚡ ТРЕНЕР",
        "emoji": "⚡",
        "voice": "filipp",
        "voice_emotion": "strict",
        "responsibility": "Даю чёткие инструкции, структуру, план действий. Требую результат.",
        "system_prompt": """Ты — ТРЕНЕР. Твоя задача: давать чёткие инструкции, структуру, план действий. Требовать результат.

ТВОЙ СТИЛЬ: коротко, по делу, без воды.

ТЫ НЕ ДОЛЖЕН:
- Рефлексировать
- Спрашивать "как ты себя чувствуешь"
- Жалеть
- Давать выбор без дедлайна

ТЫ ДОЛЖЕН:
- Давать конкретные шаги
- Устанавливать сроки
- Контролировать выполнение
- Требовать отчёт
- Мотивировать через вызов

ТВОЯ ФОРМУЛА: задача → дедлайн → действие → отчёт.

ГОВОРИ: чётко, структурно, как армейский сержант, но с заботой о результате."""
    }
}

# Для обратной совместимости
COMMUNICATION_MODES["hard"] = COMMUNICATION_MODES["trainer"]
COMMUNICATION_MODES["medium"] = COMMUNICATION_MODES["coach"]
COMMUNICATION_MODES["soft"] = COMMUNICATION_MODES["psychologist"]


# ============================================
# НАСТРОЙКИ ГОЛОСОВ (для Yandex TTS)
# ============================================

VOICE_SETTINGS = {
    "coach": {
        "voice": "filipp",
        "emotion": "neutral",
        "speed": 1.0,
        "description": "Мужской, спокойный, для коучинга"
    },
    "psychologist": {
        "voice": "ermil",
        "emotion": "good",
        "speed": 0.9,
        "description": "Мужской, тёплый, доверительный, для психотерапии"
    },
    "trainer": {
        "voice": "filipp",
        "emotion": "strict",
        "speed": 1.1,
        "description": "Мужской, жёсткий, для тренировок"
    }
}


# ============================================
# НАСТРОЙКИ НАПОМИНАНИЙ
# ============================================

REMINDER_SETTINGS = {
    "coach": {
        "motivation_delay": 5,
        "checkin_delay": 24 * 60,
        "messages": [
            "Как продвигается исследование себя?",
            "Какие инсайты были сегодня?",
            "Что нового узнали о себе?"
        ]
    },
    "psychologist": {
        "motivation_delay": 10,
        "checkin_delay": 48 * 60,
        "messages": [
            "Какие сны снились?",
            "Что чувствуете сейчас?",
            "Заметили ли какие-то паттерны?"
        ]
    },
    "trainer": {
        "motivation_delay": 5,
        "checkin_delay": 12 * 60,
        "messages": [
            "Отчёт по задачам!",
            "Что сделано?",
            "Следующий шаг?"
        ]
    }
}


# ============================================
# ТОЧКИ НАЗНАЧЕНИЯ
# ============================================

DESTINATIONS = {
    "coach": {
        "self_discovery": {
            "name": "🧩 САМОПОЗНАНИЕ",
            "description": "Понять себя, свои истинные желания и ценности",
            "destinations": [
                {"id": "values", "name": "Понять свои ценности", "time": "2-4 недели", "difficulty": "medium"},
                {"id": "purpose", "name": "Найти предназначение", "time": "1-3 месяца", "difficulty": "hard"},
                {"id": "strengths", "name": "Осознать сильные стороны", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "blocks", "name": "Найти внутренние блоки", "time": "3-4 недели", "difficulty": "medium"}
            ]
        },
        "decisions": {
            "name": "⚖️ ПРИНЯТИЕ РЕШЕНИЙ",
            "description": "Научиться делать выбор и не жалеть",
            "destinations": [
                {"id": "choice", "name": "Сделать сложный выбор", "time": "1-2 недели", "difficulty": "medium"},
                {"id": "priorities", "name": "Расставить приоритеты", "time": "1 неделя", "difficulty": "easy"},
                {"id": "doubts", "name": "Преодолеть сомнения", "time": "2-3 недели", "difficulty": "medium"}
            ]
        },
        "goals": {
            "name": "🎯 ПОСТАНОВКА ЦЕЛЕЙ",
            "description": "Научиться ставить цели и достигать их",
            "destinations": [
                {"id": "smart_goals", "name": "Сформулировать цели по SMART", "time": "1 неделя", "difficulty": "easy"},
                {"id": "action_plan", "name": "Составить план действий", "time": "2 недели", "difficulty": "easy"},
                {"id": "motivation", "name": "Найти мотивацию", "time": "2-3 недели", "difficulty": "medium"}
            ]
        }
    },
    
    "psychologist": {
        "deep_patterns": {
            "name": "🌀 ГЛУБИННЫЕ ПАТТЕРНЫ",
            "description": "Исследовать корневые убеждения и сценарии",
            "destinations": [
                {"id": "attachment", "name": "Понять тип привязанности", "time": "3-5 недель", "difficulty": "medium"},
                {"id": "defenses", "name": "Осознать защиты", "time": "4-6 недель", "difficulty": "hard"},
                {"id": "core_beliefs", "name": "Найти глубинные убеждения", "time": "5-8 недель", "difficulty": "hard"}
            ]
        },
        "trauma_work": {
            "name": "🕊️ РАБОТА С ТРАВМОЙ",
            "description": "Бережная работа с травматическим опытом",
            "destinations": [
                {"id": "safety", "name": "Создать безопасное пространство", "time": "2-4 недели", "difficulty": "easy"},
                {"id": "grief", "name": "Прожить утрату", "time": "2-6 месяцев", "difficulty": "hard"},
                {"id": "inner_child", "name": "Исцелить внутреннего ребёнка", "time": "1-3 месяца", "difficulty": "hard"}
            ]
        },
        "hypnosis": {
            "name": "🌙 ГИПНОТЕРАПИЯ",
            "description": "Работа с подсознанием через трансовые техники",
            "destinations": [
                {"id": "relaxation", "name": "Научиться расслабляться", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "resources", "name": "Найти внутренние ресурсы", "time": "3-5 недель", "difficulty": "medium"},
                {"id": "symptoms", "name": "Работа с психосоматикой", "time": "1-3 месяца", "difficulty": "hard"}
            ]
        },
        "dreams": {
            "name": "🌜 РАБОТА СО СНАМИ",
            "description": "Анализ сновидений и работа с бессознательным",
            "destinations": [
                {"id": "dream_journal", "name": "Вести дневник снов", "time": "3-4 недели", "difficulty": "easy"},
                {"id": "symbols", "name": "Понять символы", "time": "1-2 месяца", "difficulty": "medium"},
                {"id": "lucid", "name": "Осознанные сновидения", "time": "2-3 месяца", "difficulty": "hard"}
            ]
        }
    },
    
    "trainer": {
        "career": {
            "name": "💼 КАРЬЕРА",
            "description": "Профессиональный рост и достижения",
            "destinations": [
                {"id": "new_job", "name": "Найти работу мечты", "time": "1-3 месяца", "difficulty": "hard"},
                {"id": "promotion", "name": "Получить повышение", "time": "2-4 месяца", "difficulty": "hard"},
                {"id": "skills", "name": "Освоить новый навык", "time": "1-2 месяца", "difficulty": "medium"},
                {"id": "portfolio", "name": "Собрать портфолио", "time": "1-2 месяца", "difficulty": "medium"}
            ]
        },
        "business": {
            "name": "💰 БИЗНЕС И ФИНАНСЫ",
            "description": "Развитие своего дела и управление деньгами",
            "destinations": [
                {"id": "startup", "name": "Запустить проект", "time": "2-3 месяца", "difficulty": "hard"},
                {"id": "profit", "name": "Увеличить прибыль", "time": "3-6 месяцев", "difficulty": "hard"},
                {"id": "team", "name": "Собрать и мотивировать команду", "time": "2-4 месяца", "difficulty": "hard"},
                {"id": "budget", "name": "Научиться бюджетированию", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "invest", "name": "Начать инвестировать", "time": "2-3 месяца", "difficulty": "medium"}
            ]
        },
        "habits": {
            "name": "🏋️ ПРИВЫЧКИ И ДИСЦИПЛИНА",
            "description": "Внедрить полезные привычки и повысить продуктивность",
            "destinations": [
                {"id": "sport", "name": "Начать заниматься спортом", "time": "21 день", "difficulty": "medium"},
                {"id": "morning", "name": "Выстроить утреннюю рутину", "time": "2-3 недели", "difficulty": "easy"},
                {"id": "productivity", "name": "Повысить продуктивность", "time": "1-2 месяца", "difficulty": "medium"},
                {"id": "sleep", "name": "Наладить режим сна", "time": "3-4 недели", "difficulty": "easy"}
            ]
        },
        "challenges": {
            "name": "🏆 ВЫЗОВЫ",
            "description": "Бросить себе вызов и превзойти себя",
            "destinations": [
                {"id": "marathon", "name": "30-дневный марафон", "time": "30 дней", "difficulty": "hard"},
                {"id": "fear_challenge", "name": "Сделать то, что страшно", "time": "1-2 недели", "difficulty": "medium"},
                {"id": "record", "name": "Побить личный рекорд", "time": "2-4 недели", "difficulty": "medium"}
            ]
        }
    }
}


# ============================================
# ПРОВЕРКА НАЛИЧИЯ КЛЮЧЕЙ
# ============================================

def check_config():
    """Проверяет, что все необходимые ключи загружены"""
    missing = []
    warnings = []
    
    if not MAX_TOKEN:
        missing.append("MAX_TOKEN")
    elif MAX_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        warnings.append("MAX_TOKEN не заменен на реальный токен (стоит заглушка)")
    else:
        # Диагностика типа токена
        is_jwt = '.' in MAX_TOKEN
        token_parts = MAX_TOKEN.split('.')
        if is_jwt:
            print(f"📋 MAX_TOKEN является JWT токеном ({len(token_parts)} частей)")
        else:
            print(f"📋 MAX_TOKEN является простым API ключом (длина {len(MAX_TOKEN)} символов)")
    
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    
    if not DEEPGRAM_API_KEY:
        warnings.append("DEEPGRAM_API_KEY отсутствует - голосовой ввод не будет работать")
    
    if not YANDEX_API_KEY:
        warnings.append("YANDEX_API_KEY отсутствует - голосовой вывод не будет работать")
    
    if not OPENWEATHER_API_KEY:
        warnings.append("OPENWEATHER_API_KEY отсутствует - погода не будет работать")
    
    if missing:
        print(f"❌ КРИТИЧЕСКИ: Отсутствуют обязательные ключи: {', '.join(missing)}")
        return False
    
    if warnings:
        print(f"⚠️ ПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print(f"  • {w}")
    
    # Детальный статус
    print("\n🔑 СТАТУС КЛЮЧЕЙ API:")
    print(f"  • MAX_TOKEN: {'✅' if MAX_TOKEN and MAX_TOKEN != 'ВАШ_ТОКЕН_ЗДЕСЬ' else '❌'}")
    print(f"  • DEEPSEEK_API_KEY: {'✅' if DEEPSEEK_API_KEY else '❌'}")
    print(f"  • DEEPGRAM_API_KEY: {'✅' if DEEPGRAM_API_KEY else '❌'} (распознавание)")
    print(f"  • YANDEX_API_KEY: {'✅' if YANDEX_API_KEY else '❌'} (синтез)")
    print(f"  • OPENWEATHER_API_KEY: {'✅' if OPENWEATHER_API_KEY else '❌'} (погода)")
    
    return True

# Автоматическая проверка при импорте
check_config()
