function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}
const csrftoken = getCookie('csrftoken');
const STATUS_LABELS = {
    PLACED: 'Order received',
    PREPARING: 'Preparing',
    READY: 'Prepared - awaiting payment',
    COMPLETED: 'Completed',
    CANCELLED: 'Cancelled',
};
const NEXT_STATUS = {
    PLACED: 'PREPARING',
    PREPARING: 'READY',
    READY: 'COMPLETED',
};
let forecastChart;
let salesChart;
let knownOrderIds = null;

function showNotification(title, message) {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `<strong>${title}</strong><span>${message}</span>`;
    container.appendChild(notification);
    setTimeout(() => notification.remove(), 7000);
}

async function loadIncomingOrders() {
    const response = await fetch('/api/orders/');
    if (!response.ok) return;
    const payload = await response.json();
    const orders = Array.isArray(payload) ? payload : payload.results;
    const orderIds = new Set(orders.map(order => order.id));
    if (knownOrderIds) {
        orders.filter(order => !knownOrderIds.has(order.id)).forEach(order => {
            showNotification('New order received', `Order #${order.id} from ${order.student_username} is waiting.`);
        });
    }
    knownOrderIds = orderIds;
    const active = orders.filter(order => !['COMPLETED', 'CANCELLED'].includes(order.status));
    document.getElementById('incoming-orders').innerHTML = active.length ? `<table><tr><th>#</th><th>Student</th><th>Items</th><th>Total</th><th>Status</th><th>Next action</th></tr>
        ${active.map(order => `<tr><td>${order.id}</td><td>${order.student_username}</td><td>${order.items.map(item => `${item.quantity}×${item.dish_name}`).join(', ')}</td><td>₹${order.total_amount}</td><td><span class="status-pill status-${order.status}">${STATUS_LABELS[order.status]}</span></td><td>${NEXT_STATUS[order.status] ? `<button class="status-action primary-btn" data-order-id="${order.id}" data-next-status="${NEXT_STATUS[order.status]}">${NEXT_STATUS[order.status] === 'PREPARING' ? 'Confirm order' : NEXT_STATUS[order.status] === 'READY' ? 'Mark prepared' : 'Confirm pickup'}</button>` : ''}</td></tr>`).join('')}</table>` : '<p class="muted">No active orders.</p>';
    document.querySelectorAll('.status-action').forEach(button => button.addEventListener('click', async () => {
        button.disabled = true;
        const response = await fetch(`/api/orders/${button.dataset.orderId}/set_status/`, {method: 'PATCH', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken}, body: JSON.stringify({status: button.dataset.nextStatus})});
        if (!response.ok) button.disabled = false;
        await loadIncomingOrders();
    }));
}

async function loadInventory() {
    const response = await fetch('/api/inventory/');
    if (!response.ok) return;
    const payload = await response.json();
    const inventory = Array.isArray(payload) ? payload : payload.results;
    document.getElementById('inventory-list').innerHTML = `<table><tr><th>Dish</th><th>Available</th><th>Update</th></tr>${inventory.map(item => `<tr><td>${item.dish_name}</td><td class="${item.quantity_available <= 5 ? 'low' : ''}">${item.quantity_available}</td><td><input type="number" min="0" value="${item.quantity_available}" data-inv-id="${item.id}" class="qty-input"></td></tr>`).join('')}</table>`;
    document.querySelectorAll('.qty-input').forEach(input => input.addEventListener('change', async () => {
        await fetch(`/api/inventory/${input.dataset.invId}/`, {method: 'PATCH', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken}, body: JSON.stringify({quantity_available: parseInt(input.value, 10)})});
        loadInventory();
    }));
}

async function loadForecast() {
    const response = await fetch('/api/forecast/');
    if (!response.ok) return;
    const forecast = await response.json();
    if (forecastChart) forecastChart.destroy();
    forecastChart = new Chart(document.getElementById('forecast-chart'), {type: 'bar', data: {labels: forecast.map(item => item.dish), datasets: [{label: 'Predicted quantity', data: forecast.map(item => item.predicted_quantity), backgroundColor: '#d9480f'}]}, options: {responsive: true, plugins: {legend: {display: false}}}});
    document.getElementById('forecast-list').innerHTML = `<details><summary>View forecast details</summary><table><tr><th>Dish</th><th>Predicted qty</th><th>Basis</th></tr>${forecast.map(item => `<tr><td>${item.dish}</td><td>${item.predicted_quantity}</td><td class="muted">${item.basis}</td></tr>`).join('')}</table></details>`;
}

async function loadSales() {
    const response = await fetch('/api/sales/');
    if (!response.ok) return;
    const data = await response.json();
    if (salesChart) salesChart.destroy();
    salesChart = new Chart(document.getElementById('sales-chart'), {type: 'bar', data: {labels: data.per_dish.map(item => item.dish__name), datasets: [{label: 'Units sold today', data: data.per_dish.map(item => item.units_sold), backgroundColor: '#2e7d32'}]}, options: {responsive: true, plugins: {legend: {display: false}}}});
    document.getElementById('sales-summary').innerHTML = `<p><strong>Revenue today: ₹${data.revenue}</strong></p>`;
}

document.getElementById('export-sales-btn').addEventListener('click', () => { window.location.href = '/api/sales/?export=csv'; });
async function refreshDashboard() { await Promise.all([loadIncomingOrders(), loadInventory()]); }
refreshDashboard(); loadForecast(); loadSales();
setInterval(refreshDashboard, 8000);
