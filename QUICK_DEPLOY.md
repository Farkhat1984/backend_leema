# ⚡ Быстрый старт развертывания

Краткая версия для опытных пользователей. Полная инструкция: [DEPLOYMENT.md](DEPLOYMENT.md)

## 🎯 Минимальные требования

- Ubuntu 22.04+ / Debian 11+
- Docker + Docker Compose
- Домен с настроенными DNS записями

## 🚀 Развертывание за 10 минут

### 1. Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh
sudo apt install docker-compose-plugin -y

# Клонирование проекта
mkdir -p /opt/fashion-platform && cd /opt/fashion-platform
git clone <your-repo> .
```

### 2. Конфигурация

```bash
# Создайте .env.production из примера
cp .env.production.example .env.production
nano .env.production

# Обязательно заполните:
# - POSTGRES_PASSWORD
# - SECRET_KEY (python3 -c "import secrets; print(secrets.token_urlsafe(64))")
# - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# - GEMINI_API_KEY
# - PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET
```

### 3. DNS записи

В панели домена создайте A-записи:
```
A    @      -> YOUR_SERVER_IP
A    www    -> YOUR_SERVER_IP
A    api    -> YOUR_SERVER_IP
```

### 4. SSL сертификаты

```bash
# Временная конфигурация для certbot
mv nginx/conf.d/leema.conf nginx/conf.d/leema.conf.disabled

# Создайте временную конфигурацию
cat > nginx/conf.d/temp.conf << 'EOF'
server {
    listen 80;
    server_name leema.kz www.leema.kz api.leema.kz;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}
EOF

# Запустите nginx
docker compose up -d nginx

# Получите сертификаты (замените email!)
docker compose run --rm certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@example.com \
    --agree-tos --no-eff-email \
    -d www.leema.kz -d leema.kz

docker compose run --rm certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@example.com \
    --agree-tos --no-eff-email \
    -d api.leema.kz

# Восстановите конфигурацию
rm nginx/conf.d/temp.conf
mv nginx/conf.d/leema.conf.disabled nginx/conf.d/leema.conf
```

### 5. Запуск

```bash
# Остановите nginx
docker compose down

# Соберите и запустите все сервисы
docker compose build
docker compose up -d

# Выполните миграции
docker compose exec backend alembic upgrade head

# Проверьте логи
docker compose logs -f
```

### 6. Проверка

```bash
# Health check
curl https://api.leema.kz/health

# Должен вернуть:
# {"status":"healthy","service":"Fashion AI Platform","version":"1.0.0","database":"connected"}
```

## 🔒 Безопасность

```bash
# Настройте firewall
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

## 🔄 Обновление

```bash
cd /opt/fashion-platform
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose exec backend alembic upgrade head
```

## 📊 Мониторинг

```bash
# Логи
docker compose logs -f [service_name]

# Статус
docker compose ps

# Ресурсы
docker stats
```

## 🆘 Проблемы?

1. **502 Bad Gateway**: `docker compose restart backend`
2. **SSL ошибки**: Проверьте сертификаты `docker compose exec nginx ls /etc/letsencrypt/live/`
3. **DB не подключается**: Проверьте `docker compose logs postgres`

Полная документация: [DEPLOYMENT.md](DEPLOYMENT.md)

## ✅ Итоговая структура

После развертывания:
- ✅ Frontend: https://www.leema.kz
- ✅ API: https://api.leema.kz
- ✅ Docs: https://api.leema.kz/docs
- ✅ Health: https://api.leema.kz/health
- ✅ PostgreSQL (internal)
- ✅ Auto SSL renewal
- ✅ Auto restart на сбое
