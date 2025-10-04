const API_URL = 'http://localhost:8000';
let token = localStorage.getItem('token');
let accountType = localStorage.getItem('accountType');

// API запрос с авторизацией
async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers
    };

    if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);

    if (response.status === 401) {
        logout();
        throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Неизвестная ошибка' }));
        throw new Error(error.detail || 'Ошибка запроса');
    }

    return await response.json();
}

// Показать алерт
function showAlert(message, type = 'info', containerId = 'alertContainer') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    container.innerHTML = '';
    container.appendChild(alert);

    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Выход
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('accountType');
    window.location.href = '/';
}

// Google Login
async function loginWithGoogle(accountType) {
    try {
        const response = await fetch(`${API_URL}/api/v1/auth/google/url?account_type=${accountType}`);
        const data = await response.json();

        localStorage.setItem('loginAccountType', accountType);
        window.location.href = data.authorization_url;
    } catch (error) {
        showAlert('Ошибка при входе: ' + error.message, 'error');
    }
}
