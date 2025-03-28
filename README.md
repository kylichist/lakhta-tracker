# Lakhta Tracker

## Описание

Простой телеграм-бот, быстро написанный на коленке с большим количеством кодогенерации. Все ради отслеживания
доступности билетов на экскурсию в Лахта Центр. Попробовать можно [тут](https://t.me/lakhta_tracker_bot).

## Сборка

### 1. Сборка Docker-образа локально

```bash
git clone https://github.com/kylichist/lakhta-tracker.git
cd lakhta-tracker
docker build -t lakhta-tracker .
```

### 2. Загрузка Docker-образа из GitHub Container Registry

```bash
docker pull ghcr.io/kylichist/lakhta-tracker:latest
docker tag ghcr.io/kylichist/lakhta-tracker:latest lakhta-tracker
```

## Запуск

```bash
docker run -d \
  --name lakhta-tracker \
  --restart unless-stopped \
  -e BOT_TOKEN=%YOUR_BOT_API_TOKEN% \
  -v lakhta-tracker-data:/app/data \
  lakhta-tracker
```

Вместо %YOUR_BOT_API_TOKEN% подставьте токен вашего бота, полученный у [@BotFather](https://t.me/BotFather). Также
опционально можно указать параметр `-e FREQUENCY=%MINUTES%`, где %MINUTES% - частота (число минут) проверки доступности билетов (по
умолчанию 5 минут).
