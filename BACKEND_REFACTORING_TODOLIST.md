# Backend Refactoring TODO List

## Дата создания: 2025-10-22

## Текущая ситуация

### Архитектура ролей
- **Users**: таблица с ролями `USER` и `ADMIN`
- **Shops**: отдельная таблица для магазинов
- Один человек может иметь оба профиля (User + Shop) через один `google_id`

### Платформы
- **Mobile**: доступ для Users (обычных и admin)
- **Web**: Admin panel для админов, Shop panel для магазинов

### Проблемы
1. ❌ **Нет модели Wardrobe** - пользовательский гардероб только в мобилке
2. ❌ **Товары магазина нельзя редактировать пользователям** - нет копирования в личную коллекцию
3. ❌ **Сгенерированные образы не сохраняются как товары** в гардеробе
4. ❌ **Все uploads в одной куче** - нет разделения shop/user/generated
5. ⚠️ **Guards неполные** - недостаточно проверок для всех сценариев
6. ⚠️ **Дублирование данных** - User и Shop хранят одинаковые поля (google_id, email, avatar)

---

## План изменений

### 🎯 Фаза 1: Модель Wardrobe (Гардероб пользователя)

#### 1.1 Создать модель UserWardrobe
```python
class WardrobeItemSource(str, enum.Enum):
    SHOP_PRODUCT = "shop_product"      # Скопирован из магазина
    GENERATED = "generated"             # Сгенерирован AI
    UPLOADED = "uploaded"               # Загружен пользователем
    PURCHASED = "purchased"             # Куплен в магазине

class UserWardrobeItem(Base):
    id: int
    user_id: int                        # FK -> users.id
    source: WardrobeItemSource
    
    # Если скопирован из магазина
    original_product_id: int | None    # FK -> products.id (nullable)
    
    # Если сгенерирован
    generation_id: int | None          # FK -> generations.id (nullable)
    
    # Пользовательские данные (можно редактировать)
    name: str
    description: str | None
    price: Decimal | None              # Пользователь может указать свою цену
    images: list[str]                  # JSON array URLs
    characteristics: dict | None        # JSON
    
    # Метаданные
    is_favorite: bool = False
    folder: str | None                 # Для организации (опционально)
    created_at: datetime
    updated_at: datetime
```

**Файлы для создания:**
- `app/models/wardrobe.py` - модель
- `app/schemas/wardrobe.py` - Pydantic схемы
- `app/services/wardrobe_service.py` - бизнес-логика
- `app/api/wardrobe.py` - endpoints
- `alembic/versions/xxx_add_wardrobe.py` - миграция

#### 1.2 Endpoints для гардероба
```
GET    /api/v1/wardrobe              - Список товаров в гардеробе
POST   /api/v1/wardrobe              - Добавить товар (upload/generate/copy)
GET    /api/v1/wardrobe/{id}         - Детали товара
PUT    /api/v1/wardrobe/{id}         - Редактировать товар
DELETE /api/v1/wardrobe/{id}         - Удалить из гардероба
POST   /api/v1/wardrobe/from-shop/{product_id} - Копировать из магазина
POST   /api/v1/wardrobe/from-generation/{generation_id} - Сохранить сгенерированное
```

### 🎯 Фаза 2: Разделение uploads

#### 2.1 Структура папок
```
uploads/
  ├── shops/
  │   └── {shop_id}/
  │       └── products/
  │           └── {product_id}/
  │               ├── image1.jpg
  │               └── image2.jpg
  ├── users/
  │   └── {user_id}/
  │       └── wardrobe/
  │           └── {wardrobe_item_id}/
  │               ├── image1.jpg
  │               └── image2.jpg
  ├── generations/
  │   └── {user_id}/
  │       ├── {generation_id}_original.jpg
  │       └── {generation_id}_result.jpg
  └── temp/
      └── (временные файлы)
```

#### 2.2 Создать upload helpers
```python
# app/core/file_upload.py

class UploadPath:
    @staticmethod
    def shop_product(shop_id: int, product_id: int, filename: str) -> str
    
    @staticmethod
    def user_wardrobe(user_id: int, wardrobe_id: int, filename: str) -> str
    
    @staticmethod
    def generation(user_id: int, generation_id: int, suffix: str) -> str
```

**Файлы для изменения:**
- `app/api/products.py` - использовать новые пути для shop products
- `app/api/generations.py` - использовать новые пути для generations
- Создать `app/core/file_upload.py` - helper для путей

### 🎯 Фаза 3: Улучшение Guards и Auth

#### 3.1 Исправить deps.py
```python
# Четко разделить:
# 1. get_current_user() - для USER и ADMIN (обе роли = User)
# 2. get_current_shop() - для Shop
# 3. get_current_admin() - только ADMIN роль

# Убрать путаницу:
# - Admin это User с role=ADMIN, не отдельная сущность
# - Shop это отдельная таблица, не User
```

#### 3.2 Улучшить guards.py
```python
# Добавить:
# - AdminOrShopOwnerChecker - для endpoints где админ или владелец магазина
# - StrictPlatformChecker - более строгие проверки платформы
# - WardrobeOwnerChecker - проверка владельца товара в гардеробе
```

**Файлы для изменения:**
- `app/api/deps.py` - улучшить комментарии и логику
- `app/api/guards.py` - добавить новые guards

### 🎯 Фаза 4: Связь Generation с Wardrobe

#### 4.1 Обновить Generation API
```python
# POST /api/v1/generations/try-on
# Добавить опцию: save_to_wardrobe: bool = False
# Если True - автоматически создать WardrobeItem

# POST /api/v1/generations/{id}/save-to-wardrobe
# Сохранить существующую генерацию в гардероб
```

**Файлы для изменения:**
- `app/api/generations.py` - добавить параметр save_to_wardrobe
- `app/services/generation_service.py` - интеграция с wardrobe_service

### 🎯 Фаза 5: Документация и тесты

#### 5.1 Документация
- Обновить `README.md` с новой архитектурой
- Создать `ARCHITECTURE.md` с диаграммами
- Добавить примеры API запросов

#### 5.2 Тесты
- Unit тесты для wardrobe_service
- Integration тесты для wardrobe API
- Тесты для file upload paths

---

## Приоритеты выполнения

### 🔥 Критично (сделать в первую очередь)
1. **Фаза 1** - Модель Wardrobe и API
2. **Фаза 2** - Разделение uploads
3. **Фаза 4** - Связь Generation с Wardrobe

### ⚡ Важно (сделать после критичного)
4. **Фаза 3** - Улучшение Guards и Auth

### 📝 Желательно (когда будет время)
5. **Фаза 5** - Документация и тесты

---

## Миграция данных

### Существующие генерации
- Скрипт для создания WardrobeItems из существующих Generation записей
- Переместить файлы из `uploads/generations/` в `uploads/generations/{user_id}/`

### Существующие products
- Переместить файлы из `uploads/products/` в `uploads/shops/{shop_id}/products/{product_id}/`

### Скрипт миграции
```bash
# Создать: scripts/migrate_uploads.py
python scripts/migrate_uploads.py --dry-run  # Проверка
python scripts/migrate_uploads.py --execute  # Выполнить
```

---

## Безопасность и валидация

### Проверки при создании WardrobeItem
- ✅ Пользователь может редактировать только СВОИ товары в гардеробе
- ✅ При копировании из магазина - проверить что product существует и approved
- ✅ При загрузке файлов - валидация типов и размеров
- ✅ Ограничение на количество товаров в гардеробе (например, 500 макс)

### File Upload Security
- ✅ Проверка расширений файлов (jpg, jpeg, png, webp)
- ✅ Проверка размера файла (макс 10MB)
- ✅ Sanitize имен файлов
- ✅ Генерация уникальных имен (UUID)

---

## Совместимость

### Обратная совместимость
- Старые API endpoints продолжают работать
- Новые поля в Generation опциональны
- Mobile app может работать без Wardrobe до обновления

### Версионирование API
- Рассмотреть `/api/v2/` если изменения breaking changes
- Или использовать feature flags для новых функций

---

## Метрики успеха

После завершения рефакторинга:
- [ ] Пользователи могут добавлять товары из магазина в свой гардероб
- [ ] Пользователи могут редактировать свои товары в гардеробе
- [ ] Сгенерированные образы автоматически сохраняются в гардероб
- [ ] Файлы организованы по папкам (shop/user/generation)
- [ ] Guards корректно разделяют доступ User/Shop/Admin
- [ ] Мобильное приложение может полноценно работать с гардеробом

---

## Вопросы для обсуждения

1. **Лимиты**: Сколько товаров может быть в гардеробе у одного пользователя?
2. **Шаринг**: Могут ли пользователи делиться своими товарами из гардероба?
3. **Синхронизация**: Нужна ли синхронизация с оригинальным товаром магазина?
4. **Рекомендации**: Использовать ли товары из гардероба для персональных рекомендаций?

---

## Следующие шаги

1. ✅ Создан коммит текущего состояния
2. ✅ Создан TODO list (этот документ)
3. 🔄 Создать документы для фронтенд команды
4. 🔄 Начать Фазу 1: Модель Wardrobe
