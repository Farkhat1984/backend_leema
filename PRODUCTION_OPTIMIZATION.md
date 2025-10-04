# 🎯 Production Optimization Guide

Рекомендации по оптимизации Fashion AI Platform для production среды.

## 🚀 Performance Optimization

### 1. PostgreSQL Tuning

Создайте файл `postgres-tuning.conf` для оптимизации PostgreSQL:

```conf
# Memory Settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 16MB

# Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Query Planner
random_page_cost = 1.1
effective_io_concurrency = 200

# Connection Settings
max_connections = 100
```

Добавьте в `docker-compose.yml`:

```yaml
postgres:
  command: postgres -c config_file=/etc/postgresql/postgresql.conf
  volumes:
    - ./postgres-tuning.conf:/etc/postgresql/postgresql.conf:ro
```

### 2. Uvicorn Workers

В production уже настроено 4 worker'а в Dockerfile:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Количество workers = (2 × количество CPU ядер) + 1

Для сервера с 2 ядрами: 4-5 workers оптимально.

### 3. Nginx Caching

Добавьте кэширование статики в `nginx/conf.d/leema.conf`:

```nginx
# Кэш для статических файлов
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# Кэш для uploads
location /uploads/ {
    alias /var/www/uploads/;
    expires 30d;
    add_header Cache-Control "public";
    access_log off;
}
```

### 4. Database Connection Pooling

Проверьте настройки в `app/database.py`:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Отключите в production
    pool_size=20,  # Размер пула соединений
    max_overflow=10,  # Дополнительные соединения
    pool_pre_ping=True,  # Проверка соединений
    pool_recycle=3600  # Пересоздание через 1 час
)
```

## 🔒 Security Hardening

### 1. Ограничение запросов (Rate Limiting)

Уже настроено в `app/main.py`:

```python
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
```

Для более строгих ограничений добавьте в `.env.production`:

```env
RATE_LIMIT_PER_MINUTE=30/minute
```

### 2. Nginx Security Headers

Уже настроены в `nginx/nginx.conf`, но можно усилить:

```nginx
# CSP (Content Security Policy)
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

# Дополнительные заголовки
add_header X-Download-Options "noopen" always;
add_header X-Permitted-Cross-Domain-Policies "none" always;
```

### 3. Скрыть версии серверов

В `nginx/nginx.conf`:

```nginx
http {
    server_tokens off;  # Скрыть версию Nginx
}
```

В `docker-compose.yml` для backend:

```yaml
backend:
  environment:
    - SERVER_SOFTWARE=API  # Скрыть версию uvicorn
```

### 4. Fail2Ban для защиты от брутфорса

```bash
# Установите fail2ban
sudo apt install fail2ban -y

# Создайте jail для nginx
sudo nano /etc/fail2ban/jail.d/nginx.conf
```

```ini
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 5
findtime = 300
bantime = 3600
```

## 📊 Monitoring & Logging

### 1. Централизованное логирование

Добавьте в `docker-compose.yml`:

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 2. Prometheus + Grafana (опционально)

Для продвинутого мониторинга:

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
```

### 3. Health Check Monitoring

Используйте внешний сервис для мониторинга:
- **UptimeRobot** (бесплатно до 50 мониторов)
- **Pingdom**
- **StatusCake**

Настройте проверку: `https://api.leema.kz/health` каждые 5 минут.

## 💾 Backup Strategy

### 1. Автоматический бэкап БД (ежедневно)

```bash
# Создайте скрипт
sudo nano /opt/backup-db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/db"
DATE=$(date +%Y%m%d)
KEEP_DAYS=7

mkdir -p $BACKUP_DIR

# Бэкап базы
docker compose exec -T postgres pg_dump -U fashionuser fashion_platform | \
    gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Удалить старые бэкапы
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +$KEEP_DAYS -delete

# Отправить на S3 (опционально)
# aws s3 cp $BACKUP_DIR/db_$DATE.sql.gz s3://your-bucket/backups/
```

```bash
chmod +x /opt/backup-db.sh

# Добавьте в cron
crontab -e
```

```cron
0 3 * * * /opt/backup-db.sh >> /var/log/backup.log 2>&1
```

### 2. Бэкап uploads в S3/Yandex Object Storage

Для масштабирования рекомендуется использовать облачное хранилище:

```bash
# Установите AWS CLI или Yandex CLI
pip install awscli

# Синхронизация uploads с S3
aws s3 sync /opt/fashion-platform/uploads s3://your-bucket/uploads/ --delete
```

Добавьте в cron:
```cron
0 */6 * * * aws s3 sync /opt/fashion-platform/uploads s3://your-bucket/uploads/ --delete
```

## 🌐 CDN Integration

Для ускорения загрузки статики и uploads используйте CDN:

### 1. Cloudflare (рекомендуется)

- Бесплатный план включает:
  - CDN для всех ресурсов
  - DDoS защита
  - SSL сертификаты
  - Кэширование

Настройка:
1. Добавьте домен в Cloudflare
2. Измените NS записи у регистратора
3. Включите "Full (strict)" SSL режим
4. Настройте Page Rules для кэширования

### 2. Yandex Cloud CDN

```bash
# Создайте CDN ресурс для uploads
yc cdn resource create \
    --cname cdn.leema.kz \
    --origin-protocol https \
    --origin api.leema.kz:/uploads
```

## 🔄 Zero-Downtime Deployment

### 1. Blue-Green Deployment

Создайте `docker-compose.blue-green.yml`:

```yaml
services:
  backend-blue:
    build: .
    container_name: fashion_backend_blue
    # ... остальная конфигурация
  
  backend-green:
    build: .
    container_name: fashion_backend_green
    # ... остальная конфигурация

  nginx:
    depends_on:
      - backend-blue
      - backend-green
```

В nginx используйте upstream:

```nginx
upstream backend_servers {
    server backend-blue:8000 max_fails=3 fail_timeout=30s;
    server backend-green:8000 max_fails=3 fail_timeout=30s backup;
}

server {
    location /api/ {
        proxy_pass http://backend_servers;
    }
}
```

### 2. Rolling Update Script

```bash
#!/bin/bash
# rolling-update.sh

echo "Starting rolling update..."

# Билдим новую версию
docker compose build backend

# Обновляем по одному контейнеру
for i in 1 2 3 4; do
    echo "Updating worker $i..."
    docker compose up -d --no-deps --scale backend=$i backend
    sleep 30  # Ждем прогрева
done

echo "Rolling update completed!"
```

## 📈 Scaling

### Горизонтальное масштабирование

```bash
# Запустите несколько backend контейнеров
docker compose up -d --scale backend=4

# Nginx автоматически распределит нагрузку
```

### Вертикальное масштабирование

Ограничьте ресурсы в `docker-compose.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## 🔍 Performance Monitoring

### 1. Мониторинг запросов

Добавьте middleware в `app/main.py`:

```python
import time
from starlette.middleware.base import BaseHTTPMiddleware

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
        return response

app.add_middleware(TimingMiddleware)
```

### 2. Database Query Logging

Для отладки медленных запросов в development:

```python
# app/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Логировать SQL запросы
)
```

В production используйте `pg_stat_statements`:

```sql
-- В PostgreSQL
CREATE EXTENSION pg_stat_statements;

-- Просмотр медленных запросов
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## ✅ Checklist перед Production

- [ ] Все секретные ключи изменены
- [ ] DEBUG=false в .env.production
- [ ] CORS настроен только для нужных доменов
- [ ] SSL сертификаты получены и работают
- [ ] Firewall настроен (только 22, 80, 443)
- [ ] Автоматические бэкапы настроены
- [ ] Мониторинг health endpoint настроен
- [ ] Логирование настроено и ротируется
- [ ] Rate limiting активирован
- [ ] PayPal в режиме "live"
- [ ] Google OAuth redirect URI обновлен
- [ ] Email SMTP настроен и работает
- [ ] Тестирование на staging среде выполнено

## 🆘 Troubleshooting Performance

### Высокая нагрузка на CPU

```bash
# Проверьте какой контейнер нагружает CPU
docker stats

# Проверьте процессы внутри контейнера
docker compose exec backend top
```

### Утечки памяти

```bash
# Мониторинг памяти
docker stats --no-stream

# Перезапустите проблемный контейнер
docker compose restart backend
```

### Медленные запросы к БД

```bash
# Войдите в PostgreSQL
docker compose exec postgres psql -U fashionuser -d fashion_platform

# Проверьте активные запросы
SELECT pid, query, state, query_start 
FROM pg_stat_activity 
WHERE state != 'idle';

# Убейте долгий запрос
SELECT pg_terminate_backend(pid);
```

## 📚 Дополнительные ресурсы

- [FastAPI Best Practices](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Nginx Tuning](https://www.nginx.com/blog/tuning-nginx/)
- [Docker Security](https://docs.docker.com/engine/security/)

---

Эти оптимизации помогут вашему приложению работать стабильно и быстро под нагрузкой! 🚀
