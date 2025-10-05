# 🚀 Пошаговая инструкция по деплою Fashion AI Platform на production

## 📋 Предварительные требования

- **Сервер**: Ubuntu 20.04+ с root доступом
- **Домен**: leema.kz (настроен и направлен на IP сервера)
- **Поддомены**: www.leema.kz, api.leema.kz (A-записи на IP сервера)
- **Минимальные ресурсы**: 2GB RAM, 2 CPU cores, 20GB disk

---

## 🔧 Шаг 1: Подготовка сервера (Ubuntu)

### 1.1 Подключение к серверу
```bash
ssh root@ваш_ip_сервера
```

### 1.2 Обновление системы
```bash
apt update && apt upgrade -y
```

### 1.3 Установка Docker
```bash
# Удаление старых версий (если есть)
apt remove docker docker-engine docker.io containerd runc

# Установка зависимостей
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Добавление официального GPG ключа Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавление репозитория Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Проверка установки
docker --version
```

### 1.4 Установка Docker Compose
```bash
# Установка последней версии
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Установка прав
chmod +x /usr/local/bin/docker-compose

# Проверка
docker-compose --version
```

### 1.5 Запуск Docker при старте системы
```bash
systemctl enable docker
systemctl start docker
```

---

## 📦 Шаг 2: Загрузка проекта на сервер

### 2.1 Установка Git
```bash
apt install -y git
```

### 2.2 Создание директории для проекта
```bash
mkdir -p /var/www
cd /var/www
```

### 2.3 Клонирование репозитория
```bash
# Если проект в Git
git clone https://github.com/ваш_репозиторий/backend.git fashion-backend
cd fashion-backend

# ИЛИ загрузка через SCP/SFTP
# На вашем локальном компьютере (Windows):
# scp -r C:\Projects\backend root@ваш_ip:/var/www/fashion-backend
```

---

## 🔐 Шаг 3: Настройка переменных окружения

### 3.1 Создание production .env файла
```bash
cd /var/www/fashion-backend
cp .env.production.example .env.production
```

### 3.2 Редактирование .env.production
```bash
nano .env.production
```

**Обязательно измените следующие параметры:**

```env
# ============================================
# SECURITY - ВАЖНО! Сгенерируйте новый ключ
# ============================================
SECRET_KEY=ваш_новый_секретный_ключ_минимум_32_символа

# DATABASE - Установите надежный пароль
POSTGRES_PASSWORD=ваш_надежный_пароль_БД
DATABASE_URL=postgresql+asyncpg://fashionuser:ваш_надежный_пароль_БД@postgres:5432/fashion_platform

# GOOGLE OAUTH - Ваши реальные credentials
GOOGLE_CLIENT_ID=ваш_google_client_id
GOOGLE_CLIENT_SECRET=ваш_google_client_secret
GOOGLE_REDIRECT_URI=https://api.leema.kz/api/v1/auth/google/callback

# GEMINI AI - Ваш API ключ
GEMINI_API_KEY=ваш_gemini_api_key

# PAYPAL - Production credentials
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=ваш_production_paypal_client_id
PAYPAL_CLIENT_SECRET=ваш_production_paypal_client_secret

# EMAIL - Настройте для отправки уведомлений
SMTP_USER=ваш_email@gmail.com
SMTP_PASSWORD=ваш_app_password
EMAIL_FROM=ваш_email@gmail.com

# URLS - Уже настроены на ваш домен
FRONTEND_URL=https://www.leema.kz
```

**Для генерации SECRET_KEY выполните:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🌐 Шаг 4: Настройка DNS

### 4.1 Убедитесь, что DNS записи настроены:

| Тип | Имя | Значение | TTL |
|-----|-----|----------|-----|
| A | @ | ваш_ip_сервера | 3600 |
| A | www | ваш_ip_сервера | 3600 |
| A | api | ваш_ip_сервера | 3600 |

### 4.2 Проверка DNS
```bash
# На локальном компьютере или сервере
nslookup leema.kz
nslookup www.leema.kz
nslookup api.leema.kz
```

Должны вернуть IP адрес вашего сервера.

---

## 🔒 Шаг 5: Получение SSL сертификатов (Let's Encrypt)

### 5.1 Первоначальный запуск без SSL (для получения сертификата)

Временно измените nginx конфиг для получения сертификата:

```bash
cd /var/www/fashion-backend
```

### 5.2 Запуск сервисов
```bash
docker-compose up -d postgres backend nginx
```

### 5.3 Получение SSL сертификатов
```bash
# Для основного домена www.leema.kz
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d www.leema.kz -d leema.kz \
  --email ваш_email@gmail.com \
  --agree-tos \
  --no-eff-email

# Для поддомена api.leema.kz
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d api.leema.kz \
  --email ваш_email@gmail.com \
  --agree-tos \
  --no-eff-email
```

### 5.4 Перезапуск Nginx с SSL
```bash
docker-compose restart nginx
```

---

## 🚀 Шаг 6: Запуск приложения

### 6.1 Остановка всех контейнеров (если запущены)
```bash
cd /var/www/fashion-backend
docker-compose down
```

### 6.2 Сборка и запуск всех сервисов
```bash
docker-compose up -d --build
```

### 6.3 Проверка статуса контейнеров
```bash
docker-compose ps
```

Все контейнеры должны быть в статусе "Up" и "healthy":
- fashion_db (PostgreSQL)
- fashion_backend (FastAPI)
- fashion_nginx (Nginx)
- fashion_certbot (Certbot)

### 6.4 Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только backend
docker-compose logs -f backend

# Только nginx
docker-compose logs -f nginx
```

---

## 📊 Шаг 7: Инициализация базы данных

### 7.1 Применение миграций
```bash
docker-compose exec backend alembic upgrade head
```

### 7.2 Создание администратора (опционально)
```bash
docker-compose exec backend python create_admin.py
```

---

## ✅ Шаг 8: Проверка работоспособности

### 8.1 Проверка health endpoint
```bash
curl https://www.leema.kz/health
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

### 8.2 Проверка API документации
Откройте в браузере:
- https://www.leema.kz/docs - Swagger UI
- https://www.leema.kz/redoc - ReDoc
- https://api.leema.kz/api/v1/... - API endpoints

### 8.3 Проверка фронтенда
- https://www.leema.kz - Главная страница
- https://www.leema.kz/shop.html - Магазин
- https://www.leema.kz/admin.html - Админ панель

---

## 🔄 Шаг 9: Обновление приложения

### 9.1 Получение новых изменений
```bash
cd /var/www/fashion-backend
git pull origin main
```

### 9.2 Пересборка и перезапуск
```bash
docker-compose down
docker-compose up -d --build
```

### 9.3 Применение новых миграций (если есть)
```bash
docker-compose exec backend alembic upgrade head
```

---

## 🛡️ Шаг 10: Настройка файрвола (опционально, но рекомендуется)

### 10.1 Установка UFW
```bash
apt install -y ufw
```

### 10.2 Настройка правил
```bash
# Разрешить SSH
ufw allow 22/tcp

# Разрешить HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Включить firewall
ufw enable

# Проверить статус
ufw status
```

---

## 📝 Шаг 11: Автоматическое обновление SSL сертификатов

Certbot контейнер уже настроен на автоматическое обновление каждые 12 часов через docker-compose.yml.

Для ручной проверки обновления:
```bash
docker-compose exec certbot certbot renew --dry-run
```

---

## 🔍 Мониторинг и логи

### Просмотр логов в реальном времени
```bash
# Все сервисы
docker-compose logs -f

# Backend
docker-compose logs -f backend

# Nginx
docker-compose logs -f nginx

# Database
docker-compose logs -f postgres
```

### Проверка использования ресурсов
```bash
docker stats
```

### Подключение к контейнеру
```bash
# Backend
docker-compose exec backend bash

# Database
docker-compose exec postgres psql -U fashionuser -d fashion_platform
```

---

## 🐛 Troubleshooting

### Проблема: Контейнеры не запускаются
```bash
# Проверить логи
docker-compose logs

# Пересоздать контейнеры
docker-compose down -v
docker-compose up -d --build
```

### Проблема: База данных недоступна
```bash
# Проверить статус PostgreSQL
docker-compose exec postgres pg_isready

# Перезапустить БД
docker-compose restart postgres
```

### Проблема: SSL сертификаты не работают
```bash
# Проверить наличие сертификатов
docker-compose exec nginx ls -la /etc/letsencrypt/live/

# Пере-получить сертификаты
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d www.leema.kz -d leema.kz \
  --email ваш_email@gmail.com \
  --agree-tos --force-renewal
```

### Проблема: Nginx возвращает 502 Bad Gateway
```bash
# Проверить, запущен ли backend
docker-compose ps backend

# Проверить логи backend
docker-compose logs backend

# Перезапустить backend
docker-compose restart backend
```

---

## 🎯 Рекомендации по безопасности

1. **Регулярно обновляйте систему:**
   ```bash
   apt update && apt upgrade -y
   ```

2. **Используйте сильные пароли** для БД и SECRET_KEY

3. **Настройте резервное копирование БД:**
   ```bash
   # Создание backup
   docker-compose exec postgres pg_dump -U fashionuser fashion_platform > backup_$(date +%Y%m%d).sql
   ```

4. **Мониторьте логи** на предмет подозрительной активности

5. **Отключите DEBUG режим** в production (.env.production: DEBUG=false)

6. **Настройте rate limiting** (уже настроено в приложении)

---

## 📚 Полезные команды

```bash
# Остановить все контейнеры
docker-compose down

# Остановить и удалить volumes (ОСТОРОЖНО! Удалит данные БД)
docker-compose down -v

# Перезапустить определенный сервис
docker-compose restart backend

# Просмотр использования дискового пространства
docker system df

# Очистка неиспользуемых образов и контейнеров
docker system prune -a

# Экспорт БД
docker-compose exec postgres pg_dump -U fashionuser fashion_platform > backup.sql

# Импорт БД
cat backup.sql | docker-compose exec -T postgres psql -U fashionuser fashion_platform
```

---

## ✨ Готово!

Ваше приложение Fashion AI Platform теперь доступно по адресу:
- **Frontend**: https://www.leema.kz
- **API**: https://api.leema.kz
- **Docs**: https://www.leema.kz/docs

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Проверьте статус сервисов: `docker-compose ps`
3. Убедитесь, что DNS настроен правильно
4. Проверьте файрвол и открытые порты
