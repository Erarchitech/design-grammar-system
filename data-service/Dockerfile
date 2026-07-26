FROM python:3.11-slim

# Обновляем и ставим зависимости ОС
# git: Phase 35-13's recognition eval harness (tests/recognition_eval/arms.py)
# resolves the pre-35-08 few-shot fixture via `git show <sha>:<path>` at run
# time against the /mnt/repo bind mount (docker-compose.yml) -- without the
# git binary this raises FileNotFoundError, not just inside a container that
# lacks a live source checkout.
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем Python зависимости
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь сервис
COPY . .

# Запуск приложения
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]