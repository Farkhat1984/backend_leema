# API Changes - Image Management Update

## Дата: 2025-10-25
## Версия: 1.1.0

---

## 📋 Краткое описание изменений

Исправлено управление изображениями в системе. Теперь изображения корректно удаляются при удалении из wardrobe и добавлен новый endpoint для удаления AI генераций.

---

## 🆕 Новые API Endpoints

### DELETE /api/generations/{generation_id}

**Описание:** Удаление AI генерации вместе с изображениями.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `generation_id` (integer, required) - ID генерации для удаления

**Query Parameters:**
- `delete_files` (boolean, optional, default: true) - Удалять ли файлы изображений

**Response 200 (Success):**
```json
{
  "message": "Generation deleted successfully",
  "id": 123
}
```

**Response 404 (Not Found):**
```json
{
  "detail": "Generation not found"
}
```

**Response 409 (Conflict - в использовании):**
```json
{
  "detail": "Cannot delete: generation is saved in 2 wardrobe item(s). Remove from wardrobe first."
}
```

**Пример использования (Dart/Flutter):**
```dart
Future<void> deleteGeneration(int generationId, {bool deleteFiles = true}) async {
  final response = await dio.delete(
    '/api/generations/$generationId',
    queryParameters: {'delete_files': deleteFiles},
    options: Options(
      headers: {'Authorization': 'Bearer $token'},
    ),
  );
  
  if (response.statusCode == 200) {
    print('Generation deleted successfully');
  } else if (response.statusCode == 409) {
    // Генерация используется в wardrobe, сначала нужно удалить из wardrobe
    showError('Remove from wardrobe first');
  }
}
```

---

## 🔄 Изменения в существующих Endpoints

### DELETE /api/wardrobe/{wardrobe_id}

**Что изменилось:** Улучшена логика удаления файлов в зависимости от источника item'а.

**Новое поведение:**

1. **UPLOADED items** (загружено пользователем):
   - ✅ Файлы удаляются из `uploads/users/{user_id}/wardrobe/{wardrobe_id}/`
   - Поведение не изменилось

2. **SHOP_PRODUCT items** (из магазина):
   - ✅ Если `copy_files=true` был использован при добавлении, скопированные файлы теперь удаляются
   - Если `copy_files=false`, ссылки на оригинальные файлы товара остаются (правильно)

3. **GENERATED items** (AI генерация):
   - ⚠️ Файлы НЕ удаляются при удалении из wardrobe
   - Файлы принадлежат Generation записи
   - Для удаления файлов используйте новый endpoint `DELETE /api/generations/{id}`

**Запрос не изменился:**
```dart
Future<void> deleteWardrobeItem(int wardrobeId, {bool deleteFiles = true}) async {
  final response = await dio.delete(
    '/api/wardrobe/$wardrobeId',
    queryParameters: {'delete_files': deleteFiles},
  );
}
```

---

## 🎯 Рекомендуемые изменения в Flutter приложении

### 1. Добавить UI для удаления генераций

Добавьте возможность удалять старые AI генерации из истории пользователя:

```dart
class GenerationHistoryScreen extends StatelessWidget {
  Future<void> _deleteGeneration(BuildContext context, int generationId) async {
    // Показываем подтверждение
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Delete Generation'),
        content: Text('This will permanently delete the generated image. Continue?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    
    if (confirm != true) return;
    
    try {
      await apiService.deleteGeneration(generationId);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Generation deleted successfully')),
      );
      // Обновить список
      setState(() {
        _loadGenerations();
      });
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) {
        // Генерация в wardrobe
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Remove from wardrobe first'),
            action: SnackBarAction(
              label: 'Open Wardrobe',
              onPressed: () => Navigator.pushNamed(context, '/wardrobe'),
            ),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.message}')),
        );
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemBuilder: (context, index) {
        final generation = generations[index];
        return ListTile(
          leading: Image.network(generation.imageUrl),
          title: Text('Generation #${generation.id}'),
          trailing: IconButton(
            icon: Icon(Icons.delete, color: Colors.red),
            onPressed: () => _deleteGeneration(context, generation.id),
          ),
        );
      },
    );
  }
}
```

### 2. Обновить API Service

Добавьте новый метод в ваш API service:

```dart
class ApiService {
  final Dio dio;
  
  // ... existing methods
  
  /// Удалить AI генерацию
  Future<void> deleteGeneration(
    int generationId, {
    bool deleteFiles = true,
  }) async {
    final response = await dio.delete(
      '/api/generations/$generationId',
      queryParameters: {'delete_files': deleteFiles},
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to delete generation');
    }
  }
  
  /// Удалить wardrobe item
  Future<void> deleteWardrobeItem(
    int wardrobeId, {
    bool deleteFiles = true,
  }) async {
    final response = await dio.delete(
      '/api/wardrobe/$wardrobeId',
      queryParameters: {'delete_files': deleteFiles},
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to delete wardrobe item');
    }
  }
}
```

### 3. Улучшить UX при удалении из Wardrobe

При удалении GENERATED item'а из wardrobe, показывайте пользователю информацию:

```dart
Future<void> _deleteFromWardrobe(WardrobeItem item) async {
  String message = 'Delete this item from wardrobe?';
  String submessage = '';
  
  // Разное сообщение в зависимости от источника
  switch (item.source) {
    case 'uploaded':
      submessage = 'Image files will be permanently deleted.';
      break;
    case 'generated':
      submessage = 'Generated image will remain in your history.';
      break;
    case 'shop_product':
      submessage = 'Product will remain in the shop.';
      break;
  }
  
  final confirm = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('Delete Item'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(message),
          SizedBox(height: 8),
          Text(
            submessage,
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text('Cancel'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text('Delete', style: TextStyle(color: Colors.red)),
        ),
      ],
    ),
  );
  
  if (confirm == true) {
    await apiService.deleteWardrobeItem(item.id);
    // Обновить UI
  }
}
```

---

## 📊 Логика управления изображениями

### Жизненный цикл изображений по источникам:

| Источник | Где хранится | Удаляется при удалении из Wardrobe | Как удалить файл |
|----------|--------------|-----------------------------------|------------------|
| **UPLOADED** | `uploads/users/{user_id}/wardrobe/{wardrobe_id}/` | ✅ Да | Автоматически при `DELETE /api/wardrobe/{id}` |
| **SHOP_PRODUCT** (copy_files=false) | `uploads/shops/{shop_id}/products/{product_id}/` | ❌ Нет (ссылка) | Удаляется только при удалении товара |
| **SHOP_PRODUCT** (copy_files=true) | `uploads/users/{user_id}/wardrobe/{wardrobe_id}/` | ✅ Да | Автоматически при `DELETE /api/wardrobe/{id}` |
| **GENERATED** | `uploads/generations/{user_id}/{generation_id}_*.jpg` | ❌ Нет | `DELETE /api/generations/{id}` |

### Последовательность удаления GENERATED item:

1. Пользователь удаляет из wardrobe → запись удаляется, файл остается
2. Пользователь удаляет генерацию → файл удаляется

Если пользователь пытается удалить генерацию, которая еще в wardrobe:
- API вернет 409 Conflict
- Нужно сначала удалить из wardrobe, потом удалить генерацию

---

## 🧪 Тестовые сценарии

### Сценарий 1: Удаление загруженного item
```
1. Загрузить фото → создать wardrobe item (source: UPLOADED)
2. Удалить item из wardrobe
3. ✅ Проверить: файлы удалены из uploads/users/{user_id}/wardrobe/{wardrobe_id}/
```

### Сценарий 2: Удаление сгенерированного item
```
1. Создать AI генерацию
2. Сохранить в wardrobe (source: GENERATED)
3. Удалить из wardrobe
4. ✅ Проверить: файл остался в uploads/generations/{user_id}/
5. Попытаться удалить генерацию через API
6. ❌ Получить 409 (еще в wardrobe - если не удалили на шаге 3)
   ИЛИ
   ✅ Успешно удалить (если удалили на шаге 3)
7. ✅ Проверить: файл удален из uploads/generations/{user_id}/
```

### Сценарий 3: Удаление товара из магазина
```
1. Добавить товар в wardrobe с copy_files=true
2. Удалить из wardrobe
3. ✅ Проверить: скопированные файлы удалены из uploads/users/{user_id}/wardrobe/{wardrobe_id}/
4. ✅ Проверить: оригинальные файлы товара остались
```

---

## 🔧 Миграция данных

**Не требуется.** Изменения касаются только логики удаления файлов.

Существующие записи в базе данных остаются без изменений.

---

## ⚠️ Breaking Changes

**Нет breaking changes.**

Все существующие endpoints работают так же, только улучшена логика удаления файлов.

---

## 📝 Checklist для Flutter разработчика

- [ ] Добавить метод `deleteGeneration()` в API service
- [ ] Добавить UI для удаления генераций (иконка delete в истории генераций)
- [ ] Обработать ошибку 409 при попытке удалить генерацию, которая в wardrobe
- [ ] Обновить UI подтверждения удаления из wardrobe (показать разные сообщения для разных источников)
- [ ] Протестировать все сценарии удаления
- [ ] Обновить документацию API в коде (если есть)

---

## 🆘 Поддержка

При возникновении вопросов обращайтесь к backend разработчику или создавайте issue в репозитории.

---

## 📚 Дополнительные ресурсы

- [Wardrobe API Documentation](./app/api/wardrobe.py)
- [Generation API Documentation](./app/api/generations.py)
- [File Upload Documentation](./app/core/file_upload.py)
