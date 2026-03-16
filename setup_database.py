#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для однократного создания таблиц в PostgreSQL для бота "Фреди"

Запуск:
    python setup_database.py
"""

import asyncio
import asyncpg
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Строка подключения к БД (из ТЗ)
DB_DSN = "postgresql://variatica:Ben9BvM0OnppX1EVSabWQQSwTCrqkahh@dpg-d639vucr85hc73b2ge00-a/variatica"


async def create_tables():
    """Создает все таблицы в базе данных"""
    
    logger.info("🚀 Начинаем создание таблиц...")
    
    try:
        # Подключаемся к базе
        conn = await asyncpg.connect(DB_DSN)
        logger.info("✅ Подключение к базе данных установлено")
        
        # ====================== ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_users создана")
        
        # ====================== ТАБЛИЦА КОНТЕКСТА ПОЛЬЗОВАТЕЛЕЙ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_user_contexts (
                user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                
                -- 👤 ЛИЧНЫЕ ДАННЫЕ
                name TEXT,
                age INTEGER,
                gender TEXT,
                city TEXT,
                birth_date DATE,
                
                -- 🕒 ЧАСОВОЙ ПОЯС
                timezone TEXT DEFAULT 'Europe/Moscow',
                timezone_offset INTEGER DEFAULT 3,
                
                -- ⚙️ НАСТРОЙКИ
                communication_mode TEXT DEFAULT 'coach',
                last_context_update TIMESTAMP WITH TIME ZONE,
                
                -- 🌤 ПОГОДА (кэш)
                weather_cache JSONB,
                weather_cache_time TIMESTAMP WITH TIME ZONE,
                
                -- 👨‍👩‍👧‍👦 ЖИЗНЕННЫЙ КОНТЕКСТ
                family_status TEXT,
                has_children BOOLEAN DEFAULT FALSE,
                children_ages TEXT,
                work_schedule TEXT,
                job_title TEXT,
                commute_time INTEGER,
                housing_type TEXT,
                has_private_space BOOLEAN DEFAULT FALSE,
                has_car BOOLEAN DEFAULT FALSE,
                support_people TEXT,
                resistance_people TEXT,
                energy_level INTEGER,
                life_context_complete BOOLEAN DEFAULT FALSE,
                
                -- 📋 СОСТОЯНИЕ СБОРА КОНТЕКСТА
                awaiting_context TEXT,
                
                -- 🕐 ВРЕМЕННЫЕ МЕТКИ
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_user_contexts создана")
        
        # ====================== ТАБЛИЦА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_user_data (
                user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                data JSONB NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_user_data создана")
        
        # ====================== ТАБЛИЦА СЕРИАЛИЗОВАННЫХ ОБЪЕКТОВ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_context_objects (
                user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                context_data BYTEA NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_context_objects создана")
        
        # ====================== ТАБЛИЦА МАРШРУТОВ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_user_routes (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                route_data JSONB NOT NULL,
                current_step INTEGER DEFAULT 1,
                progress JSONB DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                completed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_user_routes создана")
        
        # ====================== ТАБЛИЦА РЕЗУЛЬТАТОВ ТЕСТОВ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_test_results (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                test_type TEXT NOT NULL,
                results JSONB NOT NULL,
                
                profile_code TEXT,
                perception_type TEXT,
                thinking_level INTEGER,
                
                vectors JSONB,
                behavioral_levels JSONB,
                
                deep_patterns JSONB,
                confinement_model JSONB,
                
                current_destination JSONB,
                current_route JSONB,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_test_results создана")
        
        # ====================== ТАБЛИЦА ОТВЕТОВ НА ТЕСТ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_test_answers (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                test_result_id BIGINT REFERENCES fredi_test_results(id) ON DELETE CASCADE,
                
                stage INTEGER NOT NULL,
                question_index INTEGER NOT NULL,
                question_text TEXT,
                answer_text TEXT,
                answer_value TEXT,
                
                scores JSONB,
                measures TEXT,
                strategy TEXT,
                dilts TEXT,
                pattern TEXT,
                target TEXT,
                
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_test_answers создана")
        
        # ====================== ТАБЛИЦА ГИПНОТИЧЕСКИХ ЯКОРЕЙ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_hypno_anchors (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                anchor_name TEXT NOT NULL,
                anchor_state TEXT NOT NULL,
                anchor_phrase TEXT NOT NULL,
                emoji TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_used TIMESTAMP WITH TIME ZONE,
                use_count INTEGER DEFAULT 0,
                UNIQUE(user_id, anchor_name)
            )
        """)
        logger.info("✅ Таблица fredi_hypno_anchors создана")
        
        # ====================== ТАБЛИЦА НАПОМИНАНИЙ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_reminders (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                reminder_type TEXT NOT NULL,
                remind_at TIMESTAMP WITH TIME ZONE NOT NULL,
                data JSONB,
                is_sent BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_reminders создана")
        
        # ====================== ТАБЛИЦА КЭША ИДЕЙ НА ВЫХОДНЫЕ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_weekend_ideas_cache (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                ideas_text TEXT NOT NULL,
                main_vector TEXT,
                main_level INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 hour'
            )
        """)
        logger.info("✅ Таблица fredi_weekend_ideas_cache создана")
        
        # ====================== ТАБЛИЦА КЭША АНАЛИЗА ВОПРОСОВ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_question_analysis_cache (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                question_hash INTEGER NOT NULL,
                question_text TEXT,
                analysis JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '5 minutes'
            )
        """)
        logger.info("✅ Таблица fredi_question_analysis_cache создана")
        
        # ====================== ТАБЛИЦА СОБЫТИЙ ======================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fredi_events (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                event_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ Таблица fredi_events создана")
        
        # ====================== ИНДЕКСЫ ======================
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON fredi_reminders(remind_at) WHERE is_sent = FALSE")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_user_id ON fredi_events(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON fredi_events(event_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON fredi_events(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON fredi_test_results(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_profile ON fredi_test_results(profile_code)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_weekend_cache_expires ON fredi_weekend_ideas_cache(expires_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_question_cache_hash ON fredi_question_analysis_cache(user_id, question_hash)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_question_cache_expires ON fredi_question_analysis_cache(expires_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_hypno_anchors_user ON fredi_hypno_anchors(user_id)")
        
        logger.info("✅ Все индексы созданы")
        
        # Закрываем соединение
        await conn.close()
        logger.info("✅ Соединение с базой данных закрыто")
        
        print("\n" + "="*60)
        print("🎉 ВСЕ ТАБЛИЦЫ УСПЕШНО СОЗДАНЫ!")
        print("="*60)
        print("\nТаблицы с префиксом fredi_:")
        print("  • fredi_users")
        print("  • fredi_user_contexts")
        print("  • fredi_user_data")
        print("  • fredi_context_objects")
        print("  • fredi_user_routes")
        print("  • fredi_test_results")
        print("  • fredi_test_answers")
        print("  • fredi_hypno_anchors")
        print("  • fredi_reminders")
        print("  • fredi_weekend_ideas_cache")
        print("  • fredi_question_analysis_cache")
        print("  • fredi_events")
        print("\n✅ База данных готова к работе!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        print(f"\n❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    print("="*60)
    print("🗄  СОЗДАНИЕ ТАБЛИЦ В POSTGRESQL ДЛЯ БОТА 'ФРЕДИ'")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔌 Подключение к: {DB_DSN[:50]}...")
    print()
    
    asyncio.run(create_tables())
