let selectedAmount = 0;
// accountType уже объявлен в api.js, используем его
let currentBalanceValue = 0;

console.log('Topup page loaded');
console.log('Token:', token ? 'exists' : 'missing');
console.log('Account type:', accountType);

window.onload = async function () {
    console.log('Window onload triggered');

    // Проверка авторизации
    if (!token) {
        console.error('No token found, redirecting to login');
        window.location.href = '/index.html';
        return;
    }

    // Определяем тип аккаунта и загружаем баланс
    try {
        if (accountType === 'shop') {
            const shopInfo = await apiRequest('/api/v1/shops/me');
            currentBalanceValue = shopInfo.balance || 0;
            document.getElementById('accountInfo').textContent = `Магазин: ${shopInfo.shop_name}`;
        } else if (accountType === 'user' || accountType === 'admin') {
            const userInfo = await apiRequest('/api/v1/users/me');
            currentBalanceValue = userInfo.balance || 0;
            document.getElementById('accountInfo').textContent = `Пользователь: ${userInfo.email}`;
        } else {
            window.location.href = '/index.html';
            return;
        }

        document.getElementById('currentBalance').textContent = `$${currentBalanceValue.toFixed(2)}`;
    } catch (error) {
        showAlert('Ошибка загрузки данных: ' + error.message, 'error');
    }
};

function selectAmount(amount, element) {
    console.log('selectAmount called:', amount);
    selectedAmount = amount;

    // Убираем выделение со всех опций
    document.querySelectorAll('.amount-option').forEach(opt => opt.classList.remove('selected'));

    // Выделяем выбранную опцию
    if (element) {
        element.classList.add('selected');
    }

    // Очищаем custom amount
    document.getElementById('customAmount').value = '';

    updateSummary();
}

function selectCustomAmount() {
    const customValue = parseFloat(document.getElementById('customAmount').value);
    if (!isNaN(customValue) && customValue > 0) {
        selectedAmount = customValue;

        // Убираем выделение со всех опций
        document.querySelectorAll('.amount-option').forEach(opt => opt.classList.remove('selected'));

        updateSummary();
    }
}

function selectPaymentMethod(method) {
    // Пока только PayPal, но можно добавить другие методы
    document.querySelectorAll('.payment-method').forEach(m => m.classList.remove('selected'));
    event.target.closest('.payment-method').classList.add('selected');
}

function updateSummary() {
    document.getElementById('summaryAmount').textContent = `$${selectedAmount.toFixed(2)}`;
    document.getElementById('summaryTotal').textContent = `$${selectedAmount.toFixed(2)}`;
}

async function processPayment() {
    console.log('processPayment called, amount:', selectedAmount);

    if (selectedAmount <= 0) {
        console.error('Invalid amount selected');
        showAlert('Пожалуйста, выберите сумму пополнения', 'error');
        return;
    }

    try {
        let endpoint = '';
        if (accountType === 'shop') {
            endpoint = '/api/v1/payments/shop/top-up';
        } else {
            endpoint = '/api/v1/payments/user/top-up';
        }

        console.log('Creating payment at endpoint:', endpoint);
        showAlert('Создание платежа...', 'info');

        const payment = await apiRequest(endpoint, 'POST', {
            payment_type: 'top_up',
            amount: selectedAmount
        });

        console.log('Payment created:', payment);

        if (payment.approval_url) {
            console.log('Redirecting to PayPal:', payment.approval_url);
            // Перенаправляем на PayPal
            window.location.href = payment.approval_url;
        } else {
            showAlert('Ошибка: не получен URL для оплаты', 'error');
        }
    } catch (error) {
        console.error('Payment error:', error);
        showAlert('Ошибка создания платежа: ' + error.message, 'error');
    }
}

function goBack() {
    if (accountType === 'shop') {
        window.location.href = '/shop.html';
    } else if (accountType === 'admin') {
        window.location.href = '/admin.html';
    } else {
        window.location.href = '/index.html';
    }
}
