#!/bin/bash
set -e

# Запускаем скрипт для наполнения БД
echo "Running database seeding..."
python -m scripts.seed

# Запускаем основное приложение (бота)
echo "Starting bot..."
exec python -m src.bot