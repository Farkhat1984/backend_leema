# Fashion AI Platform - Backend Architecture

## Дата: 2025-10-22

---

## 📐 Общая архитектура

### Стек технологий
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL + SQLAlchemy (async)
- **Auth**: Google OAuth 2.0 + JWT
- **File Storage**: Local filesystem (uploads/)
- **Real-time**: WebSocket
- **Task Queue**: APScheduler
- **Deployment**: Docker + Docker Compose

---

## 👥 Модель пользователей и ролей

### 1. Users (таблица `users`)

**Роли:**
- `USER` - обычный пользователь (мобильное приложение)
- `ADMIN` - администратор платформы (веб панель)

**Важно**: Admin это НЕ отдельная сущность, это User с ролью ADMIN!

```python
class User(Base):
    id: int
    google_id: str        # Уникальный ID от Google
    email: str
    name: str
    avatar_url: str
    balance: Decimal
    role: UserRole        # USER или ADMIN
    
    # Relationships
    generations: list[Generation]
    orders: list[Order]
    transactions: list[Transaction]
    wardrobe: list[UserWardrobeItem]  # НОВОЕ
```

**Сценарии использования:**
- **Обычный User**: Покупает товары, генерирует образы, управляет гардеробом (Mobile App)
- **Admin**: Модерирует контент, управляет платформой, одобряет магазины (Web Admin Panel)

### 2. Shops (таблица `shops`)

**Отдельная сущность** - магазины/продавцы

```python
class Shop(Base):
    id: int
    google_id: str        # Может совпадать с User.google_id (один человек = user + shop)
    email: str
    shop_name: str
    owner_name: str
    avatar_url: str
    balance: Decimal
    is_approved: bool     # Одобрен админом
    is_active: bool
    
    # Relationships
    products: list[Product]
    orders: list[Order]
    transactions: list[Transaction]
```

**Сценарии использования:**
- **Shop Owner**: Управляет товарами, получает заказы, смотрит аналитику (Web Shop Panel)

### 3. Один человек - несколько ролей

```
Google Account: john@gmail.com
    ↓
    ├─ User (id=1, role=USER)     → Токен: {user_id: 1, role: "user"}
    └─ Shop (id=5)                 → Токен: {shop_id: 5, role: "shop"}
```

**Переключение между ролями:**
```
Mobile: Всегда User token (для покупок и генераций)
Web:    
  - Если вход как Admin → User token с role="admin"
  - Если вход как Shop → Shop token
```

---

## 🔐 Authentication Flow

### 1. Mobile App (пользователи)

```mermaid
User → Google OAuth → Backend
                        ↓
              Check: Users table by google_id
                        ↓
              Create/Get User with role=USER
                        ↓
              Generate Token: {user_id, role: "user", platform: "mobile"}
                        ↓
              Return: {access_token, user}
```

**Login request:**
```json
POST /api/v1/auth/google/login
{
  "id_token": "...",           // Google ID token (mobile)
  "account_type": "user",
  "platform": "mobile"
}
```

### 2. Web Admin Panel

```mermaid
Admin → Google OAuth → Backend
                         ↓
               Check: Users table by google_id
                         ↓
               Get User with role=ADMIN
                         ↓
               Generate Token: {user_id, role: "admin", platform: "web"}
                         ↓
               Return: {access_token, user}
```

**Login request:**
```json
POST /api/v1/auth/google/login
{
  "code": "...",               // OAuth code (web)
  "account_type": "user",      // НЕ "admin"!
  "platform": "web"
}

// Response:
{
  "user": {
    "role": "admin"  // ← Проверяем это поле для редиректа в админку
  }
}
```

### 3. Web Shop Panel

```mermaid
Shop Owner → Google OAuth → Backend
                              ↓
                    Check: Shops table by google_id
                              ↓
                    Create/Get Shop
                              ↓
                    Generate Token: {shop_id, role: "shop", platform: "web"}
                              ↓
                    Return: {access_token, shop}
```

**Login request:**
```json
POST /api/v1/auth/google/login
{
  "code": "...",
  "account_type": "shop",      // Для магазина
  "platform": "web"
}
```

---

## 🛡️ Authorization (Guards)

### Dependency Injection

```python
# app/api/deps.py

async def get_current_user() -> User:
    """
    Для endpoints пользователей
    Проверяет: token содержит user_id
    Разрешено: USER и ADMIN роли
    """
    
async def get_current_shop() -> Shop:
    """
    Для endpoints магазинов
    Проверяет: token содержит shop_id
    Разрешено: только Shop
    """
    
async def get_current_admin() -> User:
    """
    Для admin endpoints
    Проверяет: user.role == ADMIN
    Разрешено: только ADMIN
    """
```

### Примеры использования

```python
# User endpoint (доступен USER и ADMIN)
@router.get("/users/me")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user

# Admin endpoint (только ADMIN)
@router.get("/admin/shops")
async def list_shops(
    admin: User = Depends(get_current_admin)
):
    return shops

# Shop endpoint (только Shop)
@router.get("/shops/me")
async def get_shop_profile(
    current_shop: Shop = Depends(get_current_shop)
):
    return current_shop
```

---

## 📁 File Storage Structure

### Текущая структура (ДО рефакторинга)
```
uploads/
  ├── products/           # Все товары магазинов вперемешку
  ├── generations/        # Все генерации вперемешку
  └── shop_images/        # Аватары магазинов
```

### Новая структура (ПОСЛЕ рефакторинга)
```
uploads/
  ├── shops/
  │   └── {shop_id}/
  │       └── products/
  │           └── {product_id}/
  │               ├── image_0.jpg
  │               ├── image_1.jpg
  │               └── ...
  ├── users/
  │   └── {user_id}/
  │       ├── wardrobe/
  │       │   └── {wardrobe_item_id}/
  │       │       ├── image_0.jpg
  │       │       └── ...
  │       └── avatar.jpg
  ├── generations/
  │   └── {user_id}/
  │       ├── {generation_id}_original.jpg
  │       ├── {generation_id}_result.jpg
  │       └── ...
  └── temp/
      └── (cleanup after 24h)
```

**Преимущества:**
- Легко найти файлы конкретного магазина/пользователя
- Легко удалить все файлы при удалении сущности
- Логическое разделение по типам контента
- Возможность ограничить квоту на пользователя/магазин

---

## 🗄️ Основные модели данных

### Product (товар магазина)
```python
class Product(Base):
    id: int
    shop_id: int                    # FK → shops.id
    name: str
    description: str
    price: Decimal
    images: list[str]               # JSON array URLs
    characteristics: dict           # JSON
    moderation_status: Enum         # pending/approved/rejected
    is_active: bool
    
    # Relationships
    shop: Shop
    orders: list[Order]
    generations: list[Generation]   # Try-on этого товара
```

**Важно**: Товары магазина НЕЛЬЗЯ редактировать пользователям!

### UserWardrobeItem (товар в гардеробе пользователя) 🆕
```python
class UserWardrobeItem(Base):
    id: int
    user_id: int                    # FK → users.id
    source: Enum                    # shop_product/generated/uploaded/purchased
    
    # Ссылки на источники (опционально)
    original_product_id: int        # FK → products.id (если скопирован)
    generation_id: int              # FK → generations.id (если сгенерирован)
    
    # Пользовательские данные (МОЖНО РЕДАКТИРОВАТЬ)
    name: str
    description: str
    price: Decimal
    images: list[str]               # JSON array URLs
    characteristics: dict           # JSON
    
    # Организация
    is_favorite: bool
    folder: str
    
    # Relationships
    user: User
    original_product: Product       # Если скопирован из магазина
    generation: Generation          # Если сгенерирован
```

**Ключевое отличие от Product:**
- Принадлежит пользователю (не магазину)
- Можно редактировать все поля
- Хранится в `/uploads/users/{user_id}/wardrobe/`
- НЕ проходит модерацию (личная коллекция)

### Generation (AI генерация)
```python
class Generation(Base):
    id: int
    user_id: int                    # FK → users.id
    product_id: int                 # FK → products.id (опционально)
    type: Enum                      # generation/try_on
    image_url: str
    cost: Decimal                   # Стоимость генерации
    
    # Relationships
    user: User
    product: Product
    wardrobe_item: UserWardrobeItem  # 🆕 Если сохранена в гардероб
```

### Order (заказ)
```python
class Order(Base):
    id: int
    user_id: int                    # FK → users.id (покупатель)
    shop_id: int                    # FK → shops.id (продавец)
    product_id: int                 # FK → products.id
    order_type: Enum                # purchase/rental
    status: Enum                    # pending/confirmed/completed/cancelled
    total_amount: Decimal
    
    # Relationships
    user: User
    shop: Shop
    product: Product
```

---

## 🔄 Основные процессы

### 1. Покупка товара (Mobile)
```
User (mobile) → Выбор товара → Добавить в корзину → Оплата
                                                        ↓
                                        Create Order (pending)
                                                        ↓
                                        Payment gateway
                                                        ↓
                                        Order.status = confirmed
                                                        ↓
                                        Shop получает уведомление
                                                        ↓
                                        Shop отправляет товар
                                                        ↓
                                        Order.status = completed
                                                        ↓
                        (Опционально) User добавляет в Wardrobe
```

### 2. AI генерация и сохранение (Mobile)
```
User → Upload фото → Выбор товара → Генерация (AI)
                                          ↓
                            Generation создана (cost списан)
                                          ↓
                            Результат показан пользователю
                                          ↓
               (Опционально) Сохранить в Wardrobe
                                          ↓
                      UserWardrobeItem создан (source=generated)
```

### 3. Создание и модерация товара магазина (Web)
```
Shop → Upload images → Создать товар → Product (status=pending)
                                            ↓
                                 WebSocket → Admin уведомление
                                            ↓
                        Admin → Модерация → Approve/Reject
                                            ↓
                            Product.status = approved
                            Product.is_active = true
                                            ↓
                            WebSocket → Mobile пользователи
                                            ↓
                        Товар виден в каталоге (Mobile)
```

### 4. Копирование товара в гардероб (Mobile) 🆕
```
User → Просмотр Product в каталоге → "Добавить в гардероб"
                                              ↓
                        POST /api/v1/wardrobe/from-shop/{product_id}
                                              ↓
                        Копируются: name, images, price, characteristics
                                              ↓
                        UserWardrobeItem создан (source=shop_product)
                                              ↓
                        Файлы НЕ копируются (ссылка на оригинал)
                        ИЛИ копируются в /uploads/users/{user_id}/wardrobe/
                                              ↓
                        User может редактировать свою копию
```

---

## 🌐 API Endpoints Overview

### Auth
```
POST   /api/v1/auth/google/login       - Google OAuth login
POST   /api/v1/auth/refresh             - Refresh access token
POST   /api/v1/auth/logout              - Logout
GET    /api/v1/auth/google/url          - Get OAuth URL
```

### Users (Mobile + Admin)
```
GET    /api/v1/users/me                 - Current user profile
PUT    /api/v1/users/me                 - Update profile
GET    /api/v1/users/me/balance         - Get balance
GET    /api/v1/users/me/transactions    - Transaction history
GET    /api/v1/users/me/orders          - Order history
```

### Wardrobe (Mobile) 🆕
```
GET    /api/v1/wardrobe                          - List wardrobe items
POST   /api/v1/wardrobe                          - Upload new item
GET    /api/v1/wardrobe/{id}                     - Get item details
PUT    /api/v1/wardrobe/{id}                     - Update item
DELETE /api/v1/wardrobe/{id}                     - Delete item
POST   /api/v1/wardrobe/from-shop/{product_id}  - Copy from shop
POST   /api/v1/wardrobe/from-generation/{gen_id} - Save generation
```

### Products (Mobile read, Shop write)
```
GET    /api/v1/products                 - List approved products
GET    /api/v1/products/{id}            - Product details
POST   /api/v1/products                 - Create (Shop only)
PUT    /api/v1/products/{id}            - Update (Shop only)
DELETE /api/v1/products/{id}            - Delete (Shop only)
```

### Shops (Public read, Shop owner write)
```
GET    /api/v1/shops                    - List approved shops
GET    /api/v1/shops/{id}               - Shop details
GET    /api/v1/shops/me                 - My shop profile (Shop only)
PUT    /api/v1/shops/me                 - Update profile (Shop only)
GET    /api/v1/shops/me/analytics       - Analytics (Shop only)
```

### Generations (Mobile)
```
POST   /api/v1/generations/generate     - Generate new clothing
POST   /api/v1/generations/try-on       - Try-on product (🆕 + save_to_wardrobe param)
GET    /api/v1/generations/history      - Generation history
```

### Admin (Web - Admin only)
```
GET    /api/v1/admin/dashboard          - Platform stats
GET    /api/v1/admin/users              - All users
GET    /api/v1/admin/shops              - All shops
POST   /api/v1/admin/shops/{id}/approve - Approve shop
POST   /api/v1/admin/shops/{id}/reject  - Reject shop
GET    /api/v1/admin/products/moderation - Moderation queue
POST   /api/v1/admin/products/{id}/approve - Approve product
POST   /api/v1/admin/products/{id}/reject  - Reject product
```

---

## 🔌 WebSocket Events

### Connection
```
wss://api.leema.kz/ws
Query params:
  - token: JWT access token
  - client_type: "user" | "shop" | "admin"
  - platform: "mobile" | "web"
```

### Events (Server → Client)

**Product moderation:**
```json
{
  "type": "product_moderation_completed",
  "data": {
    "product_id": 123,
    "shop_id": 5,
    "status": "approved",
    "product": {...}
  }
}
```

**Shop approval:**
```json
{
  "type": "shop_approved",
  "data": {
    "shop_id": 5,
    "shop_name": "My Store"
  }
}
```

**New shop created (broadcast to users):**
```json
{
  "type": "shop_created",
  "data": {
    "shop_id": 10,
    "shop": {...}
  }
}
```

**Wardrobe updated:** 🆕
```json
{
  "type": "wardrobe_updated",
  "data": {
    "action": "created" | "updated" | "deleted",
    "wardrobe_item_id": 123,
    "user_id": 456
  }
}
```

---

## 📊 Database Schema (Simplified)

```
users
  ├─ id (PK)
  ├─ google_id (unique)
  ├─ email (unique)
  ├─ role (USER/ADMIN)
  └─ ...

shops
  ├─ id (PK)
  ├─ google_id (unique)
  ├─ email (unique)
  ├─ is_approved
  └─ ...

products
  ├─ id (PK)
  ├─ shop_id (FK → shops.id)
  ├─ moderation_status
  ├─ is_active
  └─ ...

user_wardrobe_items 🆕
  ├─ id (PK)
  ├─ user_id (FK → users.id)
  ├─ source (enum)
  ├─ original_product_id (FK → products.id, nullable)
  ├─ generation_id (FK → generations.id, nullable)
  └─ ...

generations
  ├─ id (PK)
  ├─ user_id (FK → users.id)
  ├─ product_id (FK → products.id, nullable)
  ├─ type (generation/try_on)
  └─ ...

orders
  ├─ id (PK)
  ├─ user_id (FK → users.id)
  ├─ shop_id (FK → shops.id)
  ├─ product_id (FK → products.id)
  ├─ status
  └─ ...

transactions
  ├─ id (PK)
  ├─ user_id (FK → users.id, nullable)
  ├─ shop_id (FK → shops.id, nullable)
  ├─ amount
  ├─ type (topup/purchase/payout/etc)
  └─ ...
```

---

## 🚀 Deployment

### Docker Compose
```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - SECRET_KEY=...
      - GOOGLE_CLIENT_ID=...
    volumes:
      - ./uploads:/app/uploads
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=fashion_ai
      - POSTGRES_USER=...
      - POSTGRES_PASSWORD=...
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Environment Variables
```bash
# App
APP_NAME="Fashion AI Platform"
DEBUG=false

# Database
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/fashion_ai"

# Auth
SECRET_KEY="your-secret-key-here"
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."

# URLs
API_BASE_URL="https://api.leema.kz"
FRONTEND_URL="https://leema.kz"
WEBSOCKET_URL="wss://api.leema.kz/ws"

# Upload
UPLOAD_DIR="/app/uploads"
MAX_FILE_SIZE_MB=10

# Limits
MAX_WARDROBE_ITEMS_PER_USER=500
```

---

## 📈 Performance & Scalability

### Current bottlenecks
1. **File storage** - local filesystem (should migrate to S3/CloudFlare R2)
2. **Database** - single PostgreSQL instance (consider read replicas)
3. **AI generation** - sync processing (should use task queue like Celery)

### Future improvements
- [ ] Move uploads to object storage (S3/R2)
- [ ] Add Redis for caching and session storage
- [ ] Implement Celery for async tasks (AI generation, image processing)
- [ ] Add database read replicas
- [ ] Implement CDN for static files
- [ ] Add ElasticSearch for advanced product search

---

## 🔒 Security Considerations

### Current implementation
- ✅ JWT tokens with expiration
- ✅ Google OAuth 2.0
- ✅ Role-based access control (RBAC)
- ✅ Platform-based restrictions (web/mobile)
- ✅ File upload validation (type, size)
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ CORS configuration

### Missing (TODO)
- [ ] Rate limiting per user (currently per IP)
- [ ] Token blacklist (Redis)
- [ ] 2FA for admin accounts
- [ ] Content Security Policy (CSP) headers
- [ ] API request signing for critical operations
- [ ] Audit logging for admin actions

---

**Дата последнего обновления**: 2025-10-22
**Версия**: 1.0
**Автор**: Backend Team
