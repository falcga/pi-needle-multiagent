#!/bin/bash
set -e

echo "--- Настройка Multi-LLM Agent ---"

# 1. Проверка наличия расширения в репозитории
EXTENSION_SRC=".pi/extensions/call_junior_llm_extension.ts"

if [ ! -f "$EXTENSION_SRC" ]; then
   echo "Ошибка: Файл расширения не найден по пути $EXTENSION_SRC."
   echo "Убедитесь, что вы находитесь в корне репозитория."
   exit 1
fi

echo "Расширение найдено."

# 2. Установка Python зависимостей
echo "Установка Python зависимостей..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Зависимости установлены."
else
    echo "Ошибка: requirements.txt не найден."
    exit 1
fi

echo "--- Настройка завершена! ---"
echo "Теперь:"
echo "1. Убедитесь, что Ollama запущен."
echo "2. Выполните 'ollama pull qwen:0.5b'."
echo "3. В терминале Pi выполните '/reload' для загрузки расширения."
