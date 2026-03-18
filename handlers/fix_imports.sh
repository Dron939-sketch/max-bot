#!/bin/bash
echo "🔧 Исправление импортов..."

# Заменяем во всех файлах в папке handlers/
find /opt/render/project/src/handlers -type f -name "*.py" -exec sed -i 's/from main import db, save_user_to_db/from db_instance import db, save_user_to_db/g' {} \;
find /opt/render/project/src/handlers -type f -name "*.py" -exec sed -i 's/from main import save_user_to_db/from db_instance import save_user_to_db/g' {} \;
find /opt/render/project/src/handlers -type f -name "*.py" -exec sed -i 's/from main import db/from db_instance import db/g' {} \;

echo "✅ Импорты исправлены!"
