# 🚀 Руководство по развертыванию Fashion AI Platform

Полное пошаговое руководство по развертыванию проекта на сервере с использованием Docker.

## 📋 Предварительные требования

### На вашем локальном компьютере:
- Git
- Доступ к серверу по SSH

### На сервере (VPS/Dedicated):
- **OS**: Ubuntu 22.04 LTS или выше (рекомендуется)
- **RAM**: Минимум 2GB (рекомендуется 4GB+)
- **CPU**: 2 ядра+
- **Disk**: 20GB+ свободного места
- **Домен**: leema.kz (с настроенными DNS A-записями)

## 🔧 Шаг 1: Подготовка сервера

### 1.1 Подключитесь к серверу по SSH

```bash
ssh root@your-server-ip
# или
ssh your-username@your-server-ip
```

### 1.2 Обновите систему

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Установите Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавьте пользователя в группу docker (чтобы не использовать sudo)
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo apt install docker-compose-plugin -y

# Проверьте установку
docker --version
docker compose version
```

### 1.4 Установите дополнительные инструменты

```bash
sudo apt install -y git curl wget nano
```

## 📦 Шаг 2: Клонирование проекта

### 2.1 Создайте директорию для проекта

```bash
mkdir -p /opt/fashion-platform
cd /opt/fashion-platform
```

### 2.2 Клонируйте репозиторий

```bash
# Если у вас Git репозиторий:
git clone <your-repo-url> .

# Или загрузите файлы с локального компьютера через SCP:
# На локальном компьютере выполните:
# scp -r c:\Projects\backend/* user@your-server-ip:/opt/fashion-platform/
```

## 🔐 Шаг 3: Настройка переменных окружения

### 3.1 Создайте production .env файл

```bash
cd /opt/fashion-platform
cp .env.production.example .env.production
nano .env.production
```

### 3.2 Заполните все необходимые переменные:

**ВАЖНО! Замените следующие значения:**

```env
# Database
POSTGRES_PASSWORD=ваш_очень_сложный_пароль_1234567890

# Security - Сгенерируйте новый ключ!
SECRET_KEY=ваш_секретный_ключ_из_64_символов

# Google OAuth (получите на https://console.cloud.google.com/)
GOOGLE_CLIENT_ID=ваш-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=ваш-google-client-secret
GOOGLE_REDIRECT_URI=https://api.leema.kz/api/v1/auth/google/callback

# Google Gemini AI (получите на https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=ваш-gemini-api-key

# PayPal (получите на https://developer.paypal.com/)
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=ваш-paypal-client-id
PAYPAL_CLIENT_SECRET=ваш-paypal-client-secret
PAYPAL_WEBHOOK_ID=ваш-webhook-id

# Email
SMTP_USER=ваш-email@gmail.com
SMTP_PASSWORD=ваш-app-password
EMAIL_FROM=ваш-email@gmail.com
```

### 3.3 Сгенерируйте SECRET_KEY

```bash
# Установите Python если его нет
sudo apt install python3 -y

# Сгенерируйте ключ
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Скопируйте результат в SECRET_KEY в .env.production
```

## 🌐 Шаг 4: Настройка DNS

### 4.1 Настройте DNS записи для вашего домена

В панели управления доменом (например, nic.kz) создайте следующие A-записи:

```
A    @            -> ваш-server-ip  (leema.kz)
A    www          -> ваш-server-ip  (www.leema.kz)
A    api          -> ваш-server-ip  (api.leema.kz)
```

### 4.2 Проверьте DNS (может занять до 24 часов)

```bash
# Проверьте DNS
nslookup leema.kz
nslookup www.leema.kz
nslookup api.leema.kz

# Или используйте ping
ping leema.kz
ping www.leema.kz
ping api.leema.kz
```

## 🔒 Шаг 5: Получение SSL сертификатов (HTTPS)

### 5.1 Сначала запустите проект БЕЗ SSL (временно)

Создайте временную nginx конфигурацию для получения сертификатов:

```bash
nano nginx/conf.d/leema-temp.conf
```

Вставьте:

```nginx
server {
    listen 80;
    server_name leema.kz www.leema.kz api.leema.kz;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

### 5.2 Временно переименуйте основную конфигурацию

```bash
mv nginx/conf.d/leema.conf nginx/conf.d/leema.conf.disabled
```

### 5.3 Запустите только nginx и certbot

```bash
docker compose up -d nginx certbot
```

### 5.4 Получите SSL сертификаты

```bash
# Для www.leema.kz и leema.kz
docker compose run --rm certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email ваш-email@gmail.com \
    --agree-tos \
    --no-eff-email \
    -d www.leema.kz -d leema.kz

# Для api.leema.kz
docker compose run --rm certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email ваш-email@gmail.com \
    --agree-tos \
    --no-eff-email \
    -d api.leema.kz
```

### 5.5 Восстановите основную конфигурацию

```bash
rm nginx/conf.d/leema-temp.conf
mv nginx/conf.d/leema.conf.disabled nginx/conf.d/leema.conf
```

## 🚀 Шаг 6: Запуск проекта

### 6.1 Остановите временные контейнеры

```bash
docker compose down
```

### 6.2 Соберите и запустите все сервисы

```bash
# Сборка образов
docker compose build --no-cache

# Запуск в фоновом режиме
docker compose up -d

# Проверьте статус
docker compose ps
```

### 6.3 Проверьте логи

```bash
# Все логи
docker compose logs -f

# Только backend
docker compose logs -f backend

# Только nginx
docker compose logs -f nginx

# Только postgres
docker compose logs -f postgres
```

## 🗄️ Шаг 7: Миграции базы данных

### 7.1 Выполните миграции Alembic

```bash
# Войдите в контейнер backend
docker compose exec backend bash

# Выполните миграции
alembic upgrade head

# Выйдите из контейнера
exit
```

### 7.2 Создайте администратора (опционально)

```bash
# Войдите в контейнер
docker compose exec backend bash

# Создайте admin пользователя
python create_admin.py

# Или используйте Python напрямую
python -c "
from app.database import async_session_maker
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import asyncio

async def create_admin():
    async with async_session_maker() as db:
        admin = User(
            email='admin@leema.kz',
            full_name='Admin',
            hashed_password=get_password_hash('your_admin_password'),
            role=UserRole.ADMIN,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('Admin created!')

asyncio.run(create_admin())
"

exit
```

## ✅ Шаг 8: Проверка работоспособности

### 8.1 Проверьте доступность сайтов

В браузере откройте:

- **Frontend**: https://www.leema.kz
- **API Docs**: https://api.leema.kz/docs
- **ReDoc**: https://api.leema.kz/redoc
- **Health Check**: https://api.leema.kz/health

### 8.2 Проверьте health endpoint

```bash
curl https://api.leema.kz/health
```

Должен вернуть:
```json
{
  "status": "healthy",
  "service": "Fashion AI Platform",
  "version": "1.0.0",
  "database": "connected"
}
```

## 🔄 Шаг 9: Обновление проекта

### 9.1 Стандартное обновление (с downtime)

```bash
cd /opt/fashion-platform

# Получите последние изменения
git pull

# Пересоберите и перезапустите
docker compose down
docker compose build --no-cache
docker compose up -d

# Выполните миграции если есть
docker compose exec backend alembic upgrade head
```

### 9.2 Zero-downtime обновление (рекомендуется)

```bash
# Соберите новые образы
docker compose build

# Пересоздайте контейнеры по одному
docker compose up -d --no-deps --build backend
docker compose up -d --no-deps --build nginx

# Проверьте логи
docker compose logs -f backend
```

## 🛡️ Шаг 10: Безопасность и мониторинг

### 10.1 Настройте firewall (UFW)

```bash
# Установите UFW
sudo apt install ufw -y

# Разрешите SSH (ВАЖНО!)
sudo ufw allow 22/tcp

# Разрешите HTTP и HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Включите firewall
sudo ufw enable

# Проверьте статус
sudo ufw status
```

### 10.2 Настройте автоматическое обновление SSL сертификатов

Certbot контейнер уже настроен на автоматическое обновление каждые 12 часов.

Проверьте:
```bash
docker compose logs certbot
```

### 10.3 Настройте автозапуск при перезагрузке

```bash
# Docker Compose автоматически перезапустит контейнеры
# благодаря restart: unless-stopped

# Но убедитесь что Docker запускается при старте системы
sudo systemctl enable docker
```

### 10.4 Настройте резервное копирование

```bash
# Создайте скрипт backup
nano /opt/backup-fashion.sh
```

Вставьте:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup базы данных
docker compose exec -T postgres pg_dump -U fashionuser fashion_platform > $BACKUP_DIR/db_$DATE.sql

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/fashion-platform/uploads

# Удалите старые бэкапы (старше 7 дней)
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Сделайте исполняемым:
```bash
chmod +x /opt/backup-fashion.sh
```

Добавьте в cron (ежедневно в 3:00):
```bash
crontab -e

# Добавьте строку:
0 3 * * * /opt/backup-fashion.sh >> /var/log/fashion-backup.log 2>&1
```

## 📊 Шаг 11: Мониторинг и логи

### 11.1 Просмотр логов в реальном времени

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f backend
docker compose logs -f nginx
docker compose logs -f postgres
```

### 11.2 Проверка использования ресурсов

```bash
# Статистика контейнеров
docker stats

# Использование диска
docker system df

# Объемы
docker volume ls
```

### 11.3 Очистка старых образов

```bash
# Удалите неиспользуемые образы
docker image prune -a

# Удалите неиспользуемые volumes (ОСТОРОЖНО!)
docker volume prune
```

## 🔧 Troubleshooting (Решение проблем)

### Проблема: Контейнер не запускается

```bash
# Проверьте логи
docker compose logs backend

# Проверьте статус
docker compose ps

# Перезапустите
docker compose restart backend
```

### Проблема: База данных не подключается

```bash
# Проверьте что PostgreSQL запущен
docker compose ps postgres

# Проверьте логи PostgreSQL
docker compose logs postgres

# Проверьте переменные окружения
docker compose exec backend env | grep DATABASE_URL
```

### Проблема: SSL сертификат не работает

```bash
# Проверьте что сертификаты получены
docker compose exec nginx ls -la /etc/letsencrypt/live/

# Проверьте логи nginx
docker compose logs nginx

# Пересоздайте сертификаты
docker compose run --rm certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    -d www.leema.kz -d leema.kz --force-renewal
```

### Проблема: 502 Bad Gateway

```bash
# Проверьте что backend запущен
docker compose ps backend

# Проверьте health endpoint
curl http://localhost:8000/health

# Проверьте network
docker network ls
docker network inspect fashion-platform_frontend
```

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `docker compose logs -f`
2. Проверьте статус всех сервисов: `docker compose ps`
3. Проверьте health endpoint: `curl https://api.leema.kz/health`
4. Проверьте файрвол: `sudo ufw status`
5. Проверьте DNS: `nslookup www.leema.kz`

## 🎉 Готово!

Ваш Fashion AI Platform теперь работает на:
- **Frontend**: https://www.leema.kz
- **API**: https://api.leema.kz
- **Документация**: https://api.leema.kz/docs

Успешного запуска! 🚀
