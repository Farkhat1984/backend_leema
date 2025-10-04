console.log('🔥 shop.js VERSION 3 LOADED 🔥');

const API_URL = 'http://localhost:8000';
let token = localStorage.getItem('token');
let accountType = localStorage.getItem('accountType');

// Проверка авторизации при загрузке
window.onload = async function () {
    console.log('Loading page...');
    console.log('Token:', token);
    console.log('AccountType:', accountType);

    if (token && accountType) {
        console.log('User is authenticated, loading dashboard...');
        if (accountType === 'shop') {
            console.log('Loading shop dashboard');
            await loadShopDashboard();
        } else if (accountType === 'admin') {
            console.log('Loading admin dashboard');
            await loadAdminDashboard();
        } else {
            console.log('Unknown account type:', accountType);
            document.getElementById('loginPage').style.display = 'flex';
        }
    } else {
        console.log('User not authenticated, showing login page');
        document.getElementById('loginPage').style.display = 'flex';
    }
};

// Вход через Google
async function loginWithGoogle() {
    try {
        // По умолчанию создаем магазин, роль admin назначается вручную
        const response = await fetch(`${API_URL}/api/v1/auth/google/url?account_type=shop`);
        const data = await response.json();

        // Перенаправляем на Google OAuth
        window.location.href = data.authorization_url;
    } catch (error) {
        alert('Ошибка при получении URL авторизации: ' + error.message);
    }
}

// Выход
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('accountType');
    token = null;
    accountType = null;

    document.getElementById('shopDashboard').style.display = 'none';
    document.getElementById('adminDashboard').style.display = 'none';
    document.getElementById('loginPage').style.display = 'flex';
}

// API запрос
async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка запроса');
    }

    return await response.json();
}

// Показать уведомление
function showAlert(message, type = 'success', container = 'alertContainer') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const alertContainer = document.getElementById(container);
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// === ПАНЕЛЬ МАГАЗИНА ===

async function loadShopDashboard() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('shopDashboard').style.display = 'block';

    try {
        // Загрузка информации о магазине
        const shopInfo = await apiRequest('/api/v1/shops/me');
        document.getElementById('shopName').textContent = shopInfo.shop_name;
        document.getElementById('shopAvatar').textContent = shopInfo.shop_name[0].toUpperCase();
        document.getElementById('profileShopName').value = shopInfo.shop_name;
        document.getElementById('profileEmail').value = shopInfo.email;
        document.getElementById('profileDescription').value = shopInfo.description || '';

        // Загрузка аналитики
        const analytics = await apiRequest('/api/v1/shops/me/analytics');
        document.getElementById('totalProducts').textContent = analytics.total_products;
        document.getElementById('activeProducts').textContent = analytics.active_products;
        document.getElementById('totalViews').textContent = analytics.total_views;
        document.getElementById('totalTryOns').textContent = analytics.total_try_ons;

        // Загрузка баланса и биллинга
        document.getElementById('shopBalance').textContent = `$${shopInfo.balance.toFixed(2)}`;
        document.getElementById('shopTotalEarnings').textContent = `$${analytics.total_revenue || 0}`;

        // Загрузка транзакций
        await loadShopTransactions();

        // Загрузка активных подписок
        await loadActiveRents();

        // Загрузка товаров
        await loadShopProducts();
    } catch (error) {
        showAlert('Ошибка загрузки данных: ' + error.message, 'error');
    }
}

async function loadShopProducts() {
    console.log('🔄 loadShopProducts() called');
    try {
        const products = await apiRequest('/api/v1/shops/me/products');
        console.log('📦 Products received:', products.length, products);
        const container = document.getElementById('productsList');
        console.log('📍 Container element:', container);

        if (products.length === 0) {
            console.log('⚠️ No products, showing empty state');
            container.innerHTML = '<div class="empty-state"><p>У вас пока нет товаров</p></div>';
            return;
        }

        console.log('🎨 Rendering', products.length, 'products to DOM');
        container.innerHTML = products.map(product => {
            // Правильно формируем URL изображения
            let imageUrl = '';
            if (product.images && product.images.length > 0) {
                const img = product.images[0];
                if (img.startsWith('http://') || img.startsWith('https://')) {
                    imageUrl = img;
                } else if (img.startsWith('/')) {
                    imageUrl = `${API_URL}${img}`;
                } else {
                    imageUrl = `${API_URL}/${img}`;
                }
            }

            return `
                <div class="product-card">
                    <div class="product-image">
                        ${imageUrl
                    ? `<img src="${imageUrl}" alt="${product.name}" onerror="this.parentElement.innerHTML='Ошибка загрузки'">`
                    : '<div style="color: #999; text-align: center; padding: 40px;">Нет изображения</div>'}
                    </div>
                    <div class="product-info">
                        <div class="product-name">${product.name}</div>
                        <div class="product-price">$${product.price}</div>
                        <span class="product-status status-${product.moderation_status}">
                            ${product.moderation_status === 'pending' ? 'На модерации' :
                    product.moderation_status === 'approved' ? 'Одобрен' : 'Отклонен'}
                        </span>
                        <div class="product-actions">
                            <button class="btn btn-secondary" onclick="openEditProduct(${product.id})">Изменить</button>
                            <button class="btn btn-danger" onclick="deleteProduct(${product.id})">Удалить</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        console.log('✅ DOM updated, container.innerHTML length:', container.innerHTML.length);
        console.log('✅ Products rendered successfully');
    } catch (error) {
        console.error('❌ Error in loadShopProducts:', error);
        showAlert('Ошибка загрузки товаров: ' + error.message, 'error');
    }
}

async function updateShopProfile() {
    try {
        const data = {
            shop_name: document.getElementById('profileShopName').value,
            description: document.getElementById('profileDescription').value
        };

        await apiRequest('/api/v1/shops/me', 'PUT', data);
        showAlert('Профиль успешно обновлен', 'success');
        await loadShopDashboard();
    } catch (error) {
        showAlert('Ошибка обновления профиля: ' + error.message, 'error');
    }
}

function openAddProductModal() {
    document.getElementById('addProductModal').classList.add('active');
}

function closeAddProductModal() {
    document.getElementById('addProductModal').classList.remove('active');
    document.getElementById('productName').value = '';
    document.getElementById('productDescription').value = '';
    document.getElementById('productPrice').value = '';
    document.getElementById('productImages').value = '';
}

async function createProduct() {
    try {
        const name = document.getElementById('productName').value;
        const price = parseFloat(document.getElementById('productPrice').value);

        if (!name || !price) {
            showAlert('Заполните название и цену', 'error');
            return;
        }

        // Upload images first if any
        let imageUrls = null;
        const fileInput = document.getElementById('productImages');
        if (fileInput.files.length > 0) {
            const formData = new FormData();
            for (let file of fileInput.files) {
                formData.append('files', file);
            }

            const uploadResponse = await fetch(`${API_URL}/api/v1/products/upload-images`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Ошибка загрузки изображений');
            }

            const uploadData = await uploadResponse.json();
            imageUrls = uploadData.urls.join(',');
        }

        // Create product with form data
        const formData = new FormData();
        formData.append('name', name);
        formData.append('price', price);
        if (document.getElementById('productDescription').value) {
            formData.append('description', document.getElementById('productDescription').value);
        }
        if (imageUrls) {
            formData.append('image_urls', imageUrls);
        }

        const response = await fetch(`${API_URL}/api/v1/products/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Ошибка создания товара');
        }

        showAlert('Товар успешно создан и отправлен на модерацию', 'success');
        closeAddProductModal();
        await loadShopProducts();
    } catch (error) {
        showAlert('Ошибка создания товара: ' + error.message, 'error');
    }
}

async function openEditProduct(productId) {
    try {
        const product = await apiRequest(`/api/v1/products/${productId}`);

        document.getElementById('editProductId').value = product.id;
        document.getElementById('editProductName').value = product.name;
        document.getElementById('editProductDescription').value = product.description || '';
        document.getElementById('editProductPrice').value = product.price;

        // Show current images with delete buttons
        window.currentProductImages = product.images || [];
        updateCurrentImagesDisplay();

        document.getElementById('editProductModal').classList.add('active');
    } catch (error) {
        showAlert('Ошибка загрузки товара: ' + error.message, 'error');
    }
}

function closeEditProductModal() {
    document.getElementById('editProductModal').classList.remove('active');
}

async function updateProduct() {
    try {
        const productId = document.getElementById('editProductId').value;

        // Upload new images if any
        let newImageUrls = [];
        const fileInput = document.getElementById('editProductImages');
        if (fileInput.files.length > 0) {
            const formData = new FormData();
            for (let file of fileInput.files) {
                formData.append('files', file);
            }

            const uploadResponse = await fetch(`${API_URL}/api/v1/products/upload-images`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Ошибка загрузки изображений');
            }

            const uploadData = await uploadResponse.json();
            newImageUrls = uploadData.urls;
        }

        // Combine old images (not deleted) with new ones
        const allImages = [...(window.currentProductImages || []), ...newImageUrls];

        console.log('Текущие изображения:', window.currentProductImages);
        console.log('Новые изображения:', newImageUrls);
        console.log('Все изображения для отправки:', allImages);

        // Update product
        const data = {
            name: document.getElementById('editProductName').value,
            description: document.getElementById('editProductDescription').value || null,
            price: parseFloat(document.getElementById('editProductPrice').value),
            images: allImages  // Always send array, even if empty
        };

        console.log('Данные для обновления продукта:', data);

        await apiRequest(`/api/v1/products/${productId}`, 'PUT', data);
        showAlert('Товар успешно обновлен', 'success');
        closeEditProductModal();
        await loadShopProducts();
    } catch (error) {
        showAlert('Ошибка обновления товара: ' + error.message, 'error');
    }
}

function removeProductImage(index) {
    if (!window.currentProductImages) {
        console.error('currentProductImages не определен');
        return;
    }

    console.log('Удаление изображения по индексу:', index);
    console.log('Массив до удаления:', [...window.currentProductImages]);

    // Удаляем изображение из массива
    window.currentProductImages.splice(index, 1);

    console.log('Массив после удаления:', [...window.currentProductImages]);

    // Принудительно обновляем DOM
    updateCurrentImagesDisplay();

    showAlert('Изображение удалено. Не забудьте нажать "Сохранить"!', 'success');
}

function updateCurrentImagesDisplay() {
    const currentImagesDiv = document.getElementById('currentImages');
    if (!currentImagesDiv) return;

    if (!window.currentProductImages || window.currentProductImages.length === 0) {
        currentImagesDiv.innerHTML = '<p style="color: #999; font-size: 14px;">Изображений нет</p>';
        return;
    }

    // Полностью перерисовываем
    const imagesHTML = window.currentProductImages.map((img, idx) => {
        // Проверяем, начинается ли путь с http:// или https://
        let imageUrl;
        if (img.startsWith('http://') || img.startsWith('https://')) {
            imageUrl = img;
        } else if (img.startsWith('/')) {
            // Относительный путь от корня
            imageUrl = `${API_URL}${img}`;
        } else {
            // Путь без начального слеша
            imageUrl = `${API_URL}/${img}`;
        }

        return `
            <div style="display: inline-block; position: relative; margin: 5px;">
                <img src="${imageUrl}" style="max-width: 100px; display: block; border: 1px solid #ddd; border-radius: 4px;" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22>Ошибка</text></svg>'">
                <button type="button" onclick="removeProductImage(${idx})" style="position: absolute; top: -5px; right: -5px; background: red; color: white; border: none; cursor: pointer; padding: 4px 8px; font-size: 14px; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.3);" title="Удалить это изображение">×</button>
            </div>
        `;
    }).join('');

    currentImagesDiv.innerHTML = '<strong>Текущие изображения:</strong><br>' + imagesHTML;
}

let confirmCallback = null;

window.showConfirmDialog = function(message) {
    console.log('showConfirmDialog called with message:', message);
    return new Promise((resolve) => {
        const messageEl = document.getElementById('confirmMessage');
        const dialogEl = document.getElementById('confirmDialog');
        console.log('confirmMessage element:', messageEl);
        console.log('confirmDialog element:', dialogEl);

        messageEl.textContent = message;
        dialogEl.classList.add('active');
        confirmCallback = resolve;
        console.log('Dialog shown, waiting for user action');
    });
};

window.closeConfirmDialog = function(result) {
    console.log('closeConfirmDialog called with result:', result);
    const dialogEl = document.getElementById('confirmDialog');
    dialogEl.classList.remove('active');
    if (confirmCallback) {
        console.log('Resolving promise with:', result);
        confirmCallback(result);
        confirmCallback = null;
    } else {
        console.warn('No confirmCallback found!');
    }
};

window.deleteProduct = async function(productId) {
    console.log('deleteProduct called with ID:', productId);
    const confirmed = await window.showConfirmDialog('Вы уверены, что хотите удалить этот товар?');
    console.log('User confirmed:', confirmed);

    if (!confirmed) {
        console.log('User cancelled deletion');
        return;
    }

    console.log('Sending DELETE request for product:', productId);
    try {
        await apiRequest(`/api/v1/products/${productId}`, 'DELETE');
        console.log('Product deleted successfully');
        showAlert('Товар успешно удален', 'success');
        await loadShopProducts();
        console.log('Product list reloaded');
    } catch (error) {
        console.error('Error deleting product:', error);
        showAlert('Ошибка удаления товара: ' + error.message, 'error');
    }
};

async function loadShopTransactions() {
    try {
        const transactions = await apiRequest('/api/v1/shops/me/transactions');
        const container = document.getElementById('shopTransactions');

        if (transactions.length === 0) {
            container.innerHTML = '<p style="color: #999;">Транзакций пока нет</p>';
            return;
        }

        container.innerHTML = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid #e0e0e0;">
                        <th style="padding: 10px; text-align: left;">Дата</th>
                        <th style="padding: 10px; text-align: left;">Тип</th>
                        <th style="padding: 10px; text-align: right;">Сумма</th>
                        <th style="padding: 10px; text-align: center;">Статус</th>
                    </tr>
                </thead>
                <tbody>
                    ${transactions.map(t => {
            const typeNames = {
                product_rent: 'Аренда товара',
                product_purchase: 'Продажа товара',
                shop_payout: 'Выплата',
                top_up: 'Пополнение'
            };
            const statusNames = {
                pending: 'Ожидает',
                completed: 'Завершена',
                failed: 'Ошибка',
                refunded: 'Возврат'
            };
            const date = new Date(t.created_at).toLocaleDateString('ru-RU');
            return `
                            <tr style="border-bottom: 1px solid #f0f0f0;">
                                <td style="padding: 10px;">${date}</td>
                                <td style="padding: 10px;">${typeNames[t.type] || t.type}</td>
                                <td style="padding: 10px; text-align: right; font-weight: 600; color: ${t.amount > 0 ? '#10b981' : '#ef4444'};">
                                    ${t.amount > 0 ? '+' : ''}$${t.amount.toFixed(2)}
                                </td>
                                <td style="padding: 10px; text-align: center;">
                                    <span style="padding: 4px 12px; background: ${t.status === 'completed' ? '#d1fae5' : '#fee2e2'}; color: ${t.status === 'completed' ? '#065f46' : '#991b1b'}; border-radius: 12px; font-size: 12px;">
                                        ${statusNames[t.status] || t.status}
                                    </span>
                                </td>
                            </tr>
                        `;
        }).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Ошибка загрузки транзакций:', error);
    }
}

async function loadActiveRents() {
    try {
        const products = await apiRequest('/api/v1/shops/me/products');
        const activeRented = products.filter(p => p.is_active && p.rent_expires_at);

        const container = document.getElementById('activeRents');

        if (activeRented.length === 0) {
            container.innerHTML = '<p style="color: #999;">Нет активных подписок на товары</p>';
            return;
        }

        container.innerHTML = activeRented.map(product => {
            const expiresAt = new Date(product.rent_expires_at);
            const daysLeft = Math.ceil((expiresAt - new Date()) / (1000 * 60 * 60 * 24));
            const isExpiringSoon = daysLeft <= 3;

            return `
                <div style="padding: 15px; border: 1px solid ${isExpiringSoon ? '#fbbf24' : '#e0e0e0'}; border-radius: 10px; margin-bottom: 10px; background: ${isExpiringSoon ? '#fffbeb' : 'white'};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>${product.name}</strong>
                            <div style="color: ${isExpiringSoon ? '#d97706' : '#666'}; font-size: 14px; margin-top: 5px;">
                                ${isExpiringSoon ? '⚠️ ' : ''}Истекает через ${daysLeft} дн. (${expiresAt.toLocaleDateString('ru-RU')})
                            </div>
                        </div>
                        <button class="btn btn-primary" onclick="payRent(${product.id})">Продлить</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка загрузки подписок:', error);
    }
}

async function payRent(productId) {
    try {
        // Get settings to show rent price
        const settings = await apiRequest('/api/v1/admin/settings');
        const rentPrice = settings.find(s => s.key === 'product_rent_price_monthly')?.value || 10;

        const months = prompt(`Оплата аренды товара\n\nСтоимость: $${rentPrice}/месяц\n\nНа сколько месяцев продлить?`, '1');
        if (!months || isNaN(months) || months < 1) return;

        const payment = await apiRequest('/api/v1/payments/shop/rent-product', 'POST', {
            payment_type: 'product_rent',
            amount: rentPrice * parseInt(months),
            extra_data: {
                product_id: productId,
                months: parseInt(months)
            }
        });

        if (payment.approval_url) {
            window.open(payment.approval_url, '_blank');
            showAlert('Откройте окно PayPal для оплаты', 'success');
        }
    } catch (error) {
        showAlert('Ошибка создания платежа: ' + error.message, 'error');
    }
}

async function topUpShopBalance() {
    try {
        const amount = prompt('Введите сумму пополнения (USD):', '50');
        if (!amount || isNaN(amount) || parseFloat(amount) <= 0) return;

        const payment = await apiRequest('/api/v1/payments/shop/top-up', 'POST', {
            payment_type: 'top_up',
            amount: parseFloat(amount)
        });

        if (payment.approval_url) {
            window.open(payment.approval_url, '_blank');
            showAlert('Откройте окно PayPal для пополнения баланса', 'success');
        }
    } catch (error) {
        showAlert('Ошибка создания платежа: ' + error.message, 'error');
    }
}

// === ПАНЕЛЬ АДМИНИСТРАТОРА ===

async function loadAdminDashboard() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('adminDashboard').style.display = 'block';

    try {
        const dashboard = await apiRequest('/api/v1/admin/dashboard');
        document.getElementById('adminTotalUsers').textContent = dashboard.total_users;
        document.getElementById('adminTotalShops').textContent = dashboard.total_shops;
        document.getElementById('adminTotalProducts').textContent = dashboard.total_products;
        document.getElementById('adminPendingModeration').textContent = dashboard.pending_moderation;

        // Display balances
        document.getElementById('adminUserBalances').textContent = `$${dashboard.total_user_balances.toFixed(2)}`;
        document.getElementById('adminShopBalances').textContent = `$${dashboard.total_shop_balances.toFixed(2)}`;

        await loadModerationQueue();
    } catch (error) {
        showAlert('Ошибка загрузки данных: ' + error.message, 'error', 'adminAlertContainer');
    }
}

function switchAdminTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(tab + 'Tab').classList.add('active');

    if (tab === 'moderation') loadModerationQueue();
    if (tab === 'refunds') loadRefunds();
    if (tab === 'users') loadUsersList();
    if (tab === 'shops') loadShopsList();
    if (tab === 'settings') loadSettings();
}

async function loadUsersList() {
    try {
        const users = await apiRequest('/api/v1/admin/users');
        const container = document.getElementById('usersList');

        if (users.length === 0) {
            container.innerHTML = '<p style="color: #999;">Пользователей нет</p>';
            return;
        }

        container.innerHTML = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid #e0e0e0;">
                        <th style="padding: 10px; text-align: left;">Email</th>
                        <th style="padding: 10px; text-align: left;">Имя</th>
                        <th style="padding: 10px; text-align: right;">Баланс</th>
                        <th style="padding: 10px; text-align: center;">Бесплатно генераций</th>
                        <th style="padding: 10px; text-align: center;">Бесплатно примерок</th>
                        <th style="padding: 10px; text-align: left;">Дата регистрации</th>
                    </tr>
                </thead>
                <tbody>
                    ${users.map(user => {
            const date = new Date(user.created_at).toLocaleDateString('ru-RU');
            return `
                            <tr style="border-bottom: 1px solid #f0f0f0;">
                                <td style="padding: 10px;">${user.email}</td>
                                <td style="padding: 10px;">${user.name || 'N/A'}</td>
                                <td style="padding: 10px; text-align: right; font-weight: 600; color: #667eea;">
                                    $${user.balance.toFixed(2)}
                                </td>
                                <td style="padding: 10px; text-align: center;">${user.free_generations}</td>
                                <td style="padding: 10px; text-align: center;">${user.free_try_ons}</td>
                                <td style="padding: 10px;">${date}</td>
                            </tr>
                        `;
        }).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Ошибка загрузки пользователей:', error);
    }
}

async function loadShopsList() {
    try {
        const shops = await apiRequest('/api/v1/admin/shops');
        const container = document.getElementById('shopsList');

        if (shops.length === 0) {
            container.innerHTML = '<p style="color: #999;">Магазинов нет</p>';
            return;
        }

        container.innerHTML = `
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid #e0e0e0;">
                        <th style="padding: 10px; text-align: left;">Название</th>
                        <th style="padding: 10px; text-align: left;">Email</th>
                        <th style="padding: 10px; text-align: right;">Баланс</th>
                        <th style="padding: 10px; text-align: left;">Дата регистрации</th>
                    </tr>
                </thead>
                <tbody>
                    ${shops.map(shop => {
            const date = new Date(shop.created_at).toLocaleDateString('ru-RU');
            return `
                            <tr style="border-bottom: 1px solid #f0f0f0;">
                                <td style="padding: 10px; font-weight: 600;">${shop.shop_name}</td>
                                <td style="padding: 10px;">${shop.email}</td>
                                <td style="padding: 10px; text-align: right; font-weight: 600; color: #10b981;">
                                    $${shop.balance.toFixed(2)}
                                </td>
                                <td style="padding: 10px;">${date}</td>
                            </tr>
                        `;
        }).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Ошибка загрузки магазинов:', error);
    }
}

async function loadModerationQueue() {
    try {
        const products = await apiRequest('/api/v1/admin/moderation/queue');
        const container = document.getElementById('moderationQueue');

        if (products.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>Нет товаров на модерации</p></div>';
            return;
        }

        container.innerHTML = products.map(product => `
            <div class="product-card">
                <div class="product-image">
                    ${product.images && product.images.length > 0
                ? `<img src="${product.images[0]}" alt="${product.name}">`
                : 'Нет изображения'}
                </div>
                <div class="product-info">
                    <div class="product-name">${product.name}</div>
                    <div class="product-price">$${product.price}</div>
                    <p style="font-size: 13px; color: #666; margin: 8px 0;">
                        ${product.description || 'Нет описания'}
                    </p>
                    <div class="product-actions">
                        <button class="btn btn-success" onclick="moderateProduct(${product.id}, 'approve')">Одобрить</button>
                        <button class="btn btn-danger" onclick="moderateProduct(${product.id}, 'reject')">Отклонить</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        showAlert('Ошибка загрузки очереди: ' + error.message, 'error', 'adminAlertContainer');
    }
}

async function moderateProduct(productId, action) {
    try {
        let notes = null;

        // For rejection, require notes
        if (action === 'reject') {
            notes = prompt('Укажите причину отклонения товара:');
            if (!notes || notes.trim().length === 0) {
                showAlert('Необходимо указать причину отклонения', 'error', 'adminAlertContainer');
                return;
            }
        }

        const endpoint = action === 'approve'
            ? `/api/v1/admin/moderation/${productId}/approve`
            : `/api/v1/admin/moderation/${productId}/reject`;

        await apiRequest(endpoint, 'POST', { action, notes });
        showAlert(`Товар успешно ${action === 'approve' ? 'одобрен' : 'отклонен'}`, 'success', 'adminAlertContainer');
        await loadModerationQueue();
        await loadAdminDashboard();
    } catch (error) {
        showAlert('Ошибка модерации: ' + error.message, 'error', 'adminAlertContainer');
    }
}

async function loadRefunds() {
    try {
        const status = document.getElementById('refundStatusFilter').value;
        const refunds = await apiRequest(`/api/v1/admin/refunds${status ? '?status=' + status : ''}`);
        const container = document.getElementById('refundsList');

        if (refunds.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>Нет запросов на возврат</p></div>';
            return;
        }

        container.innerHTML = refunds.map(refund => `
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <p><strong>ID:</strong> ${refund.id}</p>
                <p><strong>Причина:</strong> ${refund.reason}</p>
                <p><strong>Статус:</strong> ${refund.status}</p>
                ${refund.status === 'pending' ? `
                    <div style="margin-top: 10px;">
                        <button class="btn btn-success" onclick="processRefund(${refund.id}, 'approve')">Одобрить</button>
                        <button class="btn btn-danger" onclick="processRefund(${refund.id}, 'reject')">Отклонить</button>
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (error) {
        showAlert('Ошибка загрузки возвратов: ' + error.message, 'error', 'adminAlertContainer');
    }
}

async function processRefund(refundId, action) {
    try {
        await apiRequest(`/api/v1/admin/refunds/${refundId}/process`, 'POST', { action });
        showAlert(`Возврат ${action === 'approve' ? 'одобрен' : 'отклонен'}`, 'success', 'adminAlertContainer');
        await loadRefunds();
    } catch (error) {
        showAlert('Ошибка обработки возврата: ' + error.message, 'error', 'adminAlertContainer');
    }
}

async function loadSettings() {
    try {
        const settings = await apiRequest('/api/v1/admin/settings');
        const container = document.getElementById('settingsList');

        container.innerHTML = settings.map(setting => `
            <div class="form-group">
                <label>${setting.description || setting.key}</label>
                <input type="text" value="${setting.value}" id="setting_${setting.key}">
                <button class="btn btn-primary" onclick="updateSetting('${setting.key}')">Сохранить</button>
            </div>
        `).join('');
    } catch (error) {
        showAlert('Ошибка загрузки настроек: ' + error.message, 'error', 'adminAlertContainer');
    }
}

async function updateSetting(key) {
    try {
        const value = document.getElementById(`setting_${key}`).value;
        await apiRequest(`/api/v1/admin/settings/${key}`, 'PUT', { key, value });
        showAlert('Настройка обновлена', 'success', 'adminAlertContainer');
    } catch (error) {
        showAlert('Ошибка обновления настройки: ' + error.message, 'error', 'adminAlertContainer');
    }
}

// Make other functions globally accessible for inline onclick handlers
window.openEditProduct = openEditProduct;
window.updateShopProfile = updateShopProfile;
window.saveProduct = saveProduct;
window.removeProductImage = removeProductImage;
window.handleRefund = handleRefund;
window.moderateProduct = moderateProduct;
window.updatePlatformSetting = updatePlatformSetting;
