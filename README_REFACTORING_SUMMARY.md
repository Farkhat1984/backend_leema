# 📝 Краткая сводка: Что сделано и что дальше

## ✅ Что сделано

### 1. Создан коммит текущего состояния
```
Commit: 9c842e2
Message: "Current state: User/Shop/Admin architecture with role-based access control"
```

### 2. Создана документация (4 файла)

#### 📘 ARCHITECTURE.md (21KB)
**Для кого**: Все (техлид, разработчики, новые члены команды)
**Что внутри**:
- Полная схема архитектуры системы
- Модели данных (User, Shop, Product, Wardrobe)
- Authentication flow для всех ролей
- API endpoints overview
- WebSocket события
- Структура файлового хранилища
- Security considerations

#### 📗 BACKEND_REFACTORING_TODOLIST.md (12KB)
**Для кого**: Backend разработчики
**Что внутри**:
- 5 фаз рефакторинга с приоритетами
- **Фаза 1 (критично)**: Модель Wardrobe и API endpoints
- **Фаза 2 (критично)**: Реорганизация uploads (разделение по папкам)
- **Фаза 3 (важно)**: Улучшение Guards и Auth
- **Фаза 4 (критично)**: Связь Generation с Wardrobe
- **Фаза 5 (желательно)**: Документация и тесты
- Скрипты миграции данных
- Чеклисты для каждой фазы

#### 📙 FRONTEND_WEB_CHANGES.md (14KB)
**Для кого**: Web frontend разработчики (Admin Panel + Shop Panel)
**Что внутри**:
- Уточнения по архитектуре Auth (admin = user с role, НЕ отдельная сущность!)
- Изменения в структуре uploads для товаров магазина
- Примеры кода для загрузки файлов
- Чеклист для тестирования
- Troubleshooting
- ⚠️ **ВАЖНО**: Минимальные изменения, большинство API без изменений

#### 📕 FRONTEND_MOBILE_CHANGES.md (21KB)
**Для кого**: Mobile (Flutter) разработчики
**Что внутри**:
- **Новый функционал**: Wardrobe API (полная спецификация)
- Модель `WardrobeItem` с TypeScript/Dart примерами
- 7 новых endpoints для гардероба
- Flutter примеры кода для всех операций
- Изменения в Generation API (параметр `save_to_wardrobe`)
- UI/UX рекомендации
- Миграция существующего локального гардероба
- Примеры экранов и компонентов

---

## 🎯 Ваша текущая архитектура

### ✅ Что правильно
1. **Разделение User и Shop** - это нормальный паттерн для multi-tenant систем
2. **Token-based auth** с Google OAuth - стандартный подход
3. **Role-based access control** - базовая безопасность есть
4. **Platform separation** (web/mobile) - логичное разделение

### ⚠️ Что нужно улучшить
1. **Нет модели Wardrobe на backend** - пользователи не могут управлять своими товарами
2. **Файлы в куче** - сложно управлять, риск конфликтов имен
3. **Товары магазина нельзя копировать** - пользователь не может редактировать
4. **Guards неполные** - есть путаница между admin и shop

---

## 🚀 Следующие шаги

### Приоритет 1: Фаза 1 - Модель Wardrobe (1-2 дня)

**Что делать:**
1. Создать модель `UserWardrobeItem` в `app/models/wardrobe.py`
2. Создать Pydantic схемы в `app/schemas/wardrobe.py`
3. Создать сервис в `app/services/wardrobe_service.py`
4. Создать API endpoints в `app/api/wardrobe.py`
5. Создать миграцию Alembic
6. Добавить в `main.py`: `app.include_router(wardrobe.router, ...)`

**Файлы для создания:**
```python
# app/models/wardrobe.py
from enum import Enum
from sqlalchemy import ...

class WardrobeItemSource(str, Enum):
    SHOP_PRODUCT = "shop_product"
    GENERATED = "generated"
    UPLOADED = "uploaded"
    PURCHASED = "purchased"

class UserWardrobeItem(Base):
    __tablename__ = "user_wardrobe_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    source: Mapped[WardrobeItemSource]
    original_product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("generations.id"), nullable=True)
    
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None]
    price: Mapped[Decimal | None]
    images: Mapped[list] = mapped_column(JSON)  # ["url1", "url2"]
    characteristics: Mapped[dict | None] = mapped_column(JSON)
    
    is_favorite: Mapped[bool] = mapped_column(default=False)
    folder: Mapped[str | None]
    
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wardrobe_items")
    original_product: Mapped["Product"] = relationship("Product")
    generation: Mapped["Generation"] = relationship("Generation")
```

**Миграция:**
```bash
cd /var/www/backend
alembic revision --autogenerate -m "Add user_wardrobe_items table"
alembic upgrade head
```

### Приоритет 2: Фаза 2 - Разделение uploads (1 день)

**Что делать:**
1. Создать helper `app/core/file_upload.py` с функциями для путей
2. Обновить `app/api/products.py` - использовать новые пути
3. Обновить `app/api/wardrobe.py` - сохранять в `/uploads/users/{user_id}/wardrobe/`
4. Создать скрипт миграции `scripts/migrate_uploads.py`
5. Выполнить миграцию файлов

**Пример helper:**
```python
# app/core/file_upload.py
from pathlib import Path
from app.config import settings

class UploadPath:
    @staticmethod
    def shop_product(shop_id: int, product_id: int, filename: str) -> str:
        """Get path for shop product image"""
        path = Path(settings.UPLOAD_DIR) / "shops" / str(shop_id) / "products" / str(product_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path / filename)
    
    @staticmethod
    def user_wardrobe(user_id: int, wardrobe_id: int, filename: str) -> str:
        """Get path for user wardrobe item image"""
        path = Path(settings.UPLOAD_DIR) / "users" / str(user_id) / "wardrobe" / str(wardrobe_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path / filename)
    
    @staticmethod
    def generation(user_id: int, generation_id: int, suffix: str = "result") -> str:
        """Get path for generation result"""
        path = Path(settings.UPLOAD_DIR) / "generations" / str(user_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path / f"{generation_id}_{suffix}.jpg")
```

### Приоритет 3: Фаза 4 - Generation + Wardrobe (0.5 дня)

**Что делать:**
1. Добавить параметр `save_to_wardrobe: bool = False` в `POST /api/v1/generations/try-on`
2. Если `True` - автоматически создать `UserWardrobeItem`
3. Добавить endpoint `POST /api/v1/wardrobe/from-generation/{id}`

### Приоритет 4: Фаза 3 - Улучшение Guards (0.5 дня)

**Что делать:**
1. Улучшить комментарии в `app/api/deps.py`
2. Убрать путаницу про admin (это User.role, не отдельная сущность)
3. Добавить новые guards в `app/api/guards.py`

---

## 📊 Оценка времени

| Фаза | Задача | Время | Приоритет |
|------|--------|-------|-----------|
| 1 | Модель Wardrobe + API | 1-2 дня | 🔥 Критично |
| 2 | Разделение uploads | 1 день | 🔥 Критично |
| 4 | Generation + Wardrobe | 0.5 дня | 🔥 Критично |
| 3 | Улучшение Guards | 0.5 дня | ⚡ Важно |
| 5 | Документация и тесты | 1-2 дня | 📝 Желательно |

**Всего**: 3-6 дней работы backend разработчика

---

## 📧 Коммуникация с командой

### Frontend Web (Admin + Shop)
**Отправить**: `FRONTEND_WEB_CHANGES.md`

**Ключевые моменты для обсуждения:**
- ⚠️ Admin это НЕ `account_type: "admin"`, это `account_type: "user"` с `role: "admin"`
- URL изображений изменятся (но backward compatible)
- Минимальные изменения в коде

### Frontend Mobile (Flutter)
**Отправить**: `FRONTEND_MOBILE_CHANGES.md`

**Ключевые моменты для обсуждения:**
- 🆕 Новый функционал Wardrobe - нужна реализация UI
- Интеграция с существующим локальным гардеробом
- Новый параметр в Generation API
- Примеры кода готовы - можно копировать

---

## 🎨 Ключевые решения по гардеробу

### Как работает копирование товара из магазина?

**Вариант 1: Ссылка на оригинал** (рекомендую для начала)
```python
# При копировании из магазина
wardrobe_item.images = product.images  # Те же URL
wardrobe_item.original_product_id = product.id

# Плюсы: Не дублируем файлы, экономим место
# Минусы: Если магазин удалит товар - картинки пропадут
```

**Вариант 2: Копирование файлов**
```python
# При копировании из магазина
for img_url in product.images:
    # Скопировать файл в /uploads/users/{user_id}/wardrobe/{id}/
    new_url = copy_file_to_wardrobe(img_url, user_id, wardrobe_id)
    wardrobe_item.images.append(new_url)

# Плюсы: Независимость от магазина
# Минусы: Дублирование файлов, больше места
```

**Мой совет**: Начать с Варианта 1, потом добавить опцию "Сохранить копию файлов" по желанию пользователя.

### Лимиты

Я рекомендую установить:
- **500 товаров** в гардеробе на одного пользователя
- **5 изображений** на один товар
- **10MB** на одно изображение
- **50MB** общий размер файлов на один товар

Это можно изменить в настройках (`app/config.py`).

---

## ❓ Вопросы для обсуждения с командой

1. **Копирование файлов**: Ссылка на оригинал или копия файлов?
2. **Лимиты**: 500 товаров достаточно или нужно больше?
3. **Папки/коллекции**: Нужна ли эта функция сразу или позже?
4. **Синхронизация**: Если магазин изменит цену оригинального товара - обновлять ли в гардеробе?
5. **Приватность**: Могут ли пользователи делиться своими товарами из гардероба?
6. **Модерация**: Нужна ли модерация для uploaded товаров (или только для shop products)?

---

## 📌 Резюме

### Текущая архитектура: ✅ ХОРОШАЯ
- User/Shop разделение - правильный подход
- Admin как роль User - нормально
- Token-based auth - стандартно

### Что добавляем: 🆕 WARDROBE
- Модель `UserWardrobeItem` для личных товаров пользователя
- API для управления гардеробом
- Копирование из магазина, сохранение генераций, загрузка своих
- Организация файлов по папкам

### Сохраняем: 🔒 КАК ЕСТЬ
- User/Shop/Admin роли
- Authentication flow
- Существующие API endpoints
- Backward compatibility

### Время: ⏱️ 3-6 ДНЕЙ
- Критично: Фазы 1, 2, 4 (3-3.5 дня)
- Важно: Фаза 3 (0.5 дня)
- Желательно: Фаза 5 (1-2 дня)

---

**Готово к старту?** 🚀

Начинайте с **Фазы 1** (Модель Wardrobe). Все примеры кода и инструкции в `BACKEND_REFACTORING_TODOLIST.md`.

Документы для frontend команд готовы к отправке! 📨
