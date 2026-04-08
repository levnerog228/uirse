

FROM python:3.12

# Рабочая директория
WORKDIR /app

# pip → официальный источник
RUN pip config unset global.index-url || true && \
    pip config set global.index-url https://pypi.org/simple

# Системные зависимости (ВСЁ сразу одним слоем)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# 1. СНАЧАЛА torch (самое тяжёлое)
# -----------------------------
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# -----------------------------
# 2. requirements (БЕЗ torch!)
# -----------------------------
COPY uirsmaga/requirements.txt .

RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt


# -----------------------------
# 3. sam2 (без build isolation)
# -----------------------------
COPY sam2 /app/sam2

#RUN pip install -e /app/sam2
RUN pip cache purge && \
    pip install --no-cache-dir -e /app/sam2

# -----------------------------
# 4. код приложения
# -----------------------------
COPY uirsmaga /app/uirsmaga

# PYTHONPATH
ENV PYTHONPATH=/app

# порт
EXPOSE 5001

# запуск
CMD ["gunicorn", "-b", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "uirsmaga.server:app"]