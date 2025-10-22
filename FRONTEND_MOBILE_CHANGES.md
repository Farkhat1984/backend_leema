# Изменения для Mobile App (Flutter)

## Дата: 2025-10-22

---

## 📋 Общая информация

### Что меняется
Добавляется полноценная поддержка **Гардероба пользователя** на backend с возможностью:
- Сохранять сгенерированные образы
- Копировать товары из магазина в личную коллекцию
- Редактировать свои товары (название, цена, характеристики)
- Загружать собственные изображения одежды

### Затронутые части
- ✅ **Wardrobe (Гардероб)** - НОВАЯ ФУНКЦИЯ на backend
- ✅ **Generations** - новые опции для сохранения в гардероб
- ✅ **Products** - копирование в гардероб
- ✅ **File Uploads** - новая структура хранения

---

## 🆕 Новый функционал: Wardrobe API

### 1. Модель WardrobeItem

```typescript
interface WardrobeItem {
  id: number;
  user_id: number;
  source: 'shop_product' | 'generated' | 'uploaded' | 'purchased';
  
  // Ссылки на источники (если применимо)
  original_product_id?: number;  // Если скопирован из магазина
  generation_id?: number;         // Если сгенерирован AI
  
  // Пользовательские данные (можно редактировать)
  name: string;
  description?: string;
  price?: number;
  images: string[];               // Массив URL
  characteristics?: object;       // Произвольные характеристики
  
  // Метаданные
  is_favorite: boolean;
  folder?: string;                // Для организации (папки/коллекции)
  created_at: string;             // ISO datetime
  updated_at: string;             // ISO datetime
}
```

### 2. Endpoints

#### 2.1 Получить весь гардероб

```http
GET /api/v1/wardrobe
Authorization: Bearer {user_access_token}

Query параметры:
  - skip: number (пагинация, default: 0)
  - limit: number (пагинация, default: 50)
  - source: 'shop_product' | 'generated' | 'uploaded' | 'purchased' (фильтр)
  - is_favorite: boolean (фильтр по избранному)
  - folder: string (фильтр по папке)

Response:
{
  "items": [WardrobeItem, ...],
  "total": 123,
  "page": 1,
  "page_size": 50
}
```

**Flutter пример:**
```dart
Future<List<WardrobeItem>> getWardrobe({
  int skip = 0,
  int limit = 50,
  String? source,
  bool? isFavorite,
  String? folder,
}) async {
  final queryParams = {
    'skip': skip.toString(),
    'limit': limit.toString(),
    if (source != null) 'source': source,
    if (isFavorite != null) 'is_favorite': isFavorite.toString(),
    if (folder != null) 'folder': folder,
  };
  
  final response = await dio.get(
    '/api/v1/wardrobe',
    queryParameters: queryParams,
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
  
  return (response.data['items'] as List)
      .map((json) => WardrobeItem.fromJson(json))
      .toList();
}
```

#### 2.2 Получить один товар из гардероба

```http
GET /api/v1/wardrobe/{id}
Authorization: Bearer {user_access_token}

Response: WardrobeItem
```

#### 2.3 Создать товар в гардеробе (Upload)

```http
POST /api/v1/wardrobe
Authorization: Bearer {user_access_token}
Content-Type: multipart/form-data

Form fields:
  - files: File[] (изображения, до 5 штук)
  - name: string (обязательно)
  - description: string (опционально)
  - price: number (опционально)
  - characteristics: JSON string (опционально)
  - folder: string (опционально)

Response: WardrobeItem
```

**Flutter пример:**
```dart
Future<WardrobeItem> uploadToWardrobe({
  required List<File> images,
  required String name,
  String? description,
  double? price,
  Map<String, dynamic>? characteristics,
  String? folder,
}) async {
  final formData = FormData();
  
  // Добавить изображения
  for (var image in images) {
    formData.files.add(MapEntry(
      'files',
      await MultipartFile.fromFile(image.path),
    ));
  }
  
  // Добавить данные
  formData.fields.addAll([
    MapEntry('name', name),
    if (description != null) MapEntry('description', description),
    if (price != null) MapEntry('price', price.toString()),
    if (characteristics != null) 
      MapEntry('characteristics', jsonEncode(characteristics)),
    if (folder != null) MapEntry('folder', folder),
  ]);
  
  final response = await dio.post(
    '/api/v1/wardrobe',
    data: formData,
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
  
  return WardrobeItem.fromJson(response.data);
}
```

#### 2.4 Копировать товар из магазина в гардероб

```http
POST /api/v1/wardrobe/from-shop/{product_id}
Authorization: Bearer {user_access_token}
Content-Type: application/json

Body (опционально - для кастомизации):
{
  "name": "My custom name",      // Переопределить название
  "price": 1500,                  // Изменить цену
  "folder": "Summer Collection"   // Добавить в папку
}

Response: WardrobeItem
```

**Flutter пример:**
```dart
Future<WardrobeItem> addProductToWardrobe({
  required int productId,
  String? customName,
  double? customPrice,
  String? folder,
}) async {
  final response = await dio.post(
    '/api/v1/wardrobe/from-shop/$productId',
    data: {
      if (customName != null) 'name': customName,
      if (customPrice != null) 'price': customPrice,
      if (folder != null) 'folder': folder,
    },
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
  
  return WardrobeItem.fromJson(response.data);
}
```

#### 2.5 Сохранить сгенерированный образ в гардероб

```http
POST /api/v1/wardrobe/from-generation/{generation_id}
Authorization: Bearer {user_access_token}
Content-Type: application/json

Body (опционально):
{
  "name": "AI Generated Dress",
  "price": 2000,
  "folder": "AI Creations"
}

Response: WardrobeItem
```

**Flutter пример:**
```dart
Future<WardrobeItem> saveGenerationToWardrobe({
  required int generationId,
  String? name,
  double? price,
  String? folder,
}) async {
  final response = await dio.post(
    '/api/v1/wardrobe/from-generation/$generationId',
    data: {
      if (name != null) 'name': name,
      if (price != null) 'price': price,
      if (folder != null) 'folder': folder,
    },
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
  
  return WardrobeItem.fromJson(response.data);
}
```

#### 2.6 Обновить товар в гардеробе

```http
PUT /api/v1/wardrobe/{id}
Authorization: Bearer {user_access_token}
Content-Type: application/json

Body:
{
  "name": "Updated name",
  "description": "Updated description",
  "price": 2500,
  "characteristics": {"size": "M", "color": "Blue"},
  "is_favorite": true,
  "folder": "New Folder"
}

Response: WardrobeItem
```

**Flutter пример:**
```dart
Future<WardrobeItem> updateWardrobeItem({
  required int id,
  String? name,
  String? description,
  double? price,
  Map<String, dynamic>? characteristics,
  bool? isFavorite,
  String? folder,
}) async {
  final response = await dio.put(
    '/api/v1/wardrobe/$id',
    data: {
      if (name != null) 'name': name,
      if (description != null) 'description': description,
      if (price != null) 'price': price,
      if (characteristics != null) 'characteristics': characteristics,
      if (isFavorite != null) 'is_favorite': isFavorite,
      if (folder != null) 'folder': folder,
    },
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
  
  return WardrobeItem.fromJson(response.data);
}
```

#### 2.7 Удалить товар из гардероба

```http
DELETE /api/v1/wardrobe/{id}
Authorization: Bearer {user_access_token}

Response:
{
  "message": "Item removed from wardrobe",
  "id": 123
}
```

**Flutter пример:**
```dart
Future<void> deleteWardrobeItem(int id) async {
  await dio.delete(
    '/api/v1/wardrobe/$id',
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
}
```

---

## 🔄 Изменения в Generation API

### Автоматическое сохранение в гардероб

```http
POST /api/v1/generations/try-on
Authorization: Bearer {user_access_token}
Content-Type: multipart/form-data

NEW FIELD:
  - save_to_wardrobe: boolean (default: false)

Если true - сгенерированный образ автоматически сохраняется в гардероб
```

**Flutter пример:**
```dart
Future<Generation> tryOnProduct({
  required File userImage,
  required int productId,
  bool saveToWardrobe = false,  // НОВЫЙ ПАРАМЕТР
}) async {
  final formData = FormData();
  
  formData.files.add(MapEntry(
    'user_image',
    await MultipartFile.fromFile(userImage.path),
  ));
  
  formData.fields.addAll([
    MapEntry('product_id', productId.toString()),
    MapEntry('save_to_wardrobe', saveToWardrobe.toString()),  // НОВОЕ
  ]);
  
  final response = await dio.post(
    '/api/v1/generations/try-on',
    data: formData,
    options: Options(
      headers: {'Authorization': 'Bearer $accessToken'},
    ),
  );
  
  return Generation.fromJson(response.data);
}
```

**Response расширен:**
```json
{
  "id": 456,
  "type": "try_on",
  "image_url": "/uploads/generations/1/456_result.jpg",
  "cost": 10.0,
  "created_at": "2025-10-22T18:00:00Z",
  "wardrobe_item_id": 789  // НОВОЕ: ID созданного товара в гардеробе (если save_to_wardrobe=true)
}
```

---

## 📁 Изменения в структуре файлов

### Новые пути к изображениям

**Было (все в куче):**
```
/uploads/products/abc123.jpg
/uploads/generations/def456.jpg
/uploads/shop_images/xyz789.jpg
```

**Стало (организовано):**
```
/uploads/shops/{shop_id}/products/{product_id}/image_0.jpg
/uploads/users/{user_id}/wardrobe/{wardrobe_id}/image_0.jpg
/uploads/generations/{user_id}/{generation_id}_result.jpg
```

**Что это значит для Flutter:**
- ✅ Используйте URL из API (не конструируйте сами)
- ✅ Старые URL будут работать (backward compatibility)
- ✅ Кеширование изображений работает как обычно

**Пример кеширования:**
```dart
CachedNetworkImage(
  imageUrl: wardrobeItem.images[0],  // Полный URL из API
  placeholder: (context, url) => CircularProgressIndicator(),
  errorWidget: (context, url, error) => Icon(Icons.error),
  cacheKey: 'wardrobe_${wardrobeItem.id}_0',  // Уникальный ключ
)
```

---

## 🎨 UI/UX Рекомендации

### 1. Кнопка "Добавить в гардероб" на товарах магазина

```dart
// На странице товара из магазина
ElevatedButton.icon(
  icon: Icon(Icons.add_to_photos),
  label: Text('Добавить в гардероб'),
  onPressed: () async {
    try {
      final wardrobeItem = await addProductToWardrobe(
        productId: product.id,
      );
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Добавлено в гардероб!')),
      );
      
      // Опционально: открыть страницу редактирования
      Navigator.push(context, MaterialPageRoute(
        builder: (_) => WardrobeItemEditPage(item: wardrobeItem),
      ));
    } catch (e) {
      // Обработка ошибок
    }
  },
)
```

### 2. Сохранение генерации в гардероб

```dart
// После успешной генерации
Dialog(
  child: Column(
    children: [
      Image.network(generation.imageUrl),
      Text('Образ сгенерирован!'),
      
      // Опция сохранить в гардероб
      ElevatedButton.icon(
        icon: Icon(Icons.save),
        label: Text('Сохранить в гардероб'),
        onPressed: () async {
          final wardrobeItem = await saveGenerationToWardrobe(
            generationId: generation.id,
            name: 'AI Generated ${DateTime.now()}',
          );
          
          // Показать успех
        },
      ),
    ],
  ),
)
```

### 3. Экран гардероба с фильтрами

```dart
class WardrobePage extends StatefulWidget {
  @override
  _WardrobePageState createState() => _WardrobePageState();
}

class _WardrobePageState extends State<WardrobePage> {
  String? selectedSource;
  bool? showFavorites;
  List<WardrobeItem> items = [];
  
  @override
  void initState() {
    super.initState();
    _loadWardrobe();
  }
  
  Future<void> _loadWardrobe() async {
    final result = await getWardrobe(
      source: selectedSource,
      isFavorite: showFavorites,
    );
    setState(() => items = result);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Мой гардероб'),
        actions: [
          // Фильтры
          PopupMenuButton<String>(
            icon: Icon(Icons.filter_list),
            onSelected: (value) {
              setState(() => selectedSource = value);
              _loadWardrobe();
            },
            itemBuilder: (context) => [
              PopupMenuItem(value: null, child: Text('Все')),
              PopupMenuItem(value: 'shop_product', child: Text('Из магазина')),
              PopupMenuItem(value: 'generated', child: Text('Сгенерированные')),
              PopupMenuItem(value: 'uploaded', child: Text('Загруженные')),
            ],
          ),
        ],
      ),
      body: GridView.builder(
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          childAspectRatio: 0.7,
        ),
        itemCount: items.length,
        itemBuilder: (context, index) {
          final item = items[index];
          return WardrobeItemCard(
            item: item,
            onTap: () => _editItem(item),
            onDelete: () => _deleteItem(item.id),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        child: Icon(Icons.add),
        onPressed: () => _uploadNewItem(),
      ),
    );
  }
}
```

---

## 🔐 Security & Validation

### Ограничения на стороне сервера

- ✅ Максимум 5 изображений на товар
- ✅ Размер файла: до 10MB
- ✅ Форматы: jpg, jpeg, png, webp
- ✅ Максимум 500 товаров в гардеробе у одного пользователя

### Обработка ошибок

```dart
try {
  await uploadToWardrobe(/* ... */);
} on DioError catch (e) {
  if (e.response?.statusCode == 400) {
    // Валидация данных
    final message = e.response?.data['detail'] ?? 'Неверные данные';
    showError(message);
  } else if (e.response?.statusCode == 403) {
    // Достигнут лимит товаров
    showError('Достигнут лимит товаров в гардеробе (500)');
  } else if (e.response?.statusCode == 413) {
    // Файл слишком большой
    showError('Файл слишком большой. Максимум 10MB');
  } else {
    showError('Ошибка при загрузке');
  }
}
```

---

## 🔄 Миграция существующего кода

### Если гардероб уже реализован локально

**Вариант 1: Синхронизация**
```dart
// При первом запросе после обновления - синхронизировать
Future<void> syncLocalWardrobeToServer() async {
  final localItems = await localDatabase.getAllWardrobeItems();
  
  for (var item in localItems) {
    // Проверить есть ли на сервере
    try {
      await getWardrobe(/* фильтр по ID если есть */);
    } catch (e) {
      // Если нет - загрузить на сервер
      await uploadToWardrobe(
        images: item.images,
        name: item.name,
        // ...
      );
    }
  }
}
```

**Вариант 2: Полная миграция на server-side**
```dart
// Удалить локальную БД гардероба
// Использовать только серверные данные
// Кеширование через dio_cache или hive для offline режима
```

---

## 📊 WebSocket события (если нужно)

Backend может отправлять события о изменениях в гардеробе:

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

**Flutter обработка:**
```dart
channel.stream.listen((message) {
  final data = jsonDecode(message);
  
  if (data['type'] == 'wardrobe_updated') {
    // Обновить UI
    _reloadWardrobe();
  }
});
```

---

## ✅ Checklist для внедрения

### Backend готовность
- [ ] Backend развернут с новыми endpoints
- [ ] Миграция базы данных выполнена
- [ ] Файлы перенесены в новую структуру

### Flutter изменения
- [ ] Создать модель `WardrobeItem`
- [ ] Создать API сервис для wardrobe endpoints
- [ ] Реализовать UI экрана гардероба
- [ ] Добавить кнопку "Добавить в гардероб" на товары
- [ ] Добавить опцию сохранения при генерации
- [ ] Реализовать редактирование товаров гардероба
- [ ] Реализовать загрузку собственных изображений
- [ ] Обновить кеширование изображений
- [ ] Тестирование всех сценариев

### Тестирование
- [ ] Создание товара в гардеробе (upload)
- [ ] Копирование из магазина
- [ ] Сохранение генерации
- [ ] Редактирование товара
- [ ] Удаление товара
- [ ] Фильтрация по источнику
- [ ] Избранное
- [ ] Папки/коллекции
- [ ] Лимиты (500 товаров, 10MB файлы)

---

## 🆘 Troubleshooting

### Проблема: 403 Forbidden при добавлении в гардероб
**Причина**: Достигнут лимит 500 товаров
**Решение**: Удалить старые товары или увеличить лимит на backend

### Проблема: Изображения не загружаются
**Причина**: Неверный формат файла или размер
**Решение**: Проверить формат (jpg/png/webp) и размер (<10MB)

### Проблема: Duplicate entry при копировании из магазина
**Причина**: Товар уже есть в гардеробе
**Решение**: Проверить перед добавлением или показать уведомление

---

## 📧 Примеры запросов (Postman/cURL)

### Получить гардероб
```bash
curl -X GET "https://api.leema.kz/api/v1/wardrobe?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Добавить товар из магазина
```bash
curl -X POST "https://api.leema.kz/api/v1/wardrobe/from-shop/123" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Custom Name", "folder": "Summer"}'
```

### Сохранить генерацию
```bash
curl -X POST "https://api.leema.kz/api/v1/wardrobe/from-generation/456" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "AI Dress", "price": 2000}'
```

---

**Дата последнего обновления**: 2025-10-22
**Версия Backend API**: v1
**Статус**: ✅ Ready for implementation
