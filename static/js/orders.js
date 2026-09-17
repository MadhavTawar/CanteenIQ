let currentPage = 1;
const knownStatuses = {};
const STATUS_MESSAGES = {
    PLACED: ['Order received', 'The canteen has received your order.'],
    PREPARING: ['Order confirmed', 'Your order is being prepared.'],
    READY: ['Order prepared', 'Your order is ready. Pay at the counter to receive it.'],
    COMPLETED: ['Thank you', 'Your order has been completed. Thank you for ordering with CanteenIQ.'],
    CANCELLED: ['Order cancelled', 'Your order was cancelled by the canteen.'],
};
const STATUS_LABELS = {
    PLACED: 'Order received',
    PREPARING: 'Preparing',
    READY: 'Prepared - awaiting payment',
    COMPLETED: 'Completed',
    CANCELLED: 'Cancelled',
};

function showNotification(title, message) {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerHTML = `<strong>${title}</strong><span>${message}</span>`;
    container.appendChild(notification);
    setTimeout(() => notification.remove(), 7000);
}

function queryString() {
    const params = new URLSearchParams(new FormData(document.getElementById('order-filters')));
    params.set('page', currentPage);
    return params.toString();
}

function renderOrders(payload) {
    const orders = Array.isArray(payload) ? payload : payload.results;
    orders.forEach(order => {
        if (knownStatuses[order.id] && knownStatuses[order.id] !== order.status) {
            const message = STATUS_MESSAGES[order.status];
            showNotification(message[0], `Order #${order.id}: ${message[1]}`);
        }
        knownStatuses[order.id] = order.status;
    });
    const container = document.getElementById('orders-list');
    container.innerHTML = orders.length ? orders.map(order => `
        <div class="order-card"><div class="order-header"><strong>Order #${order.id}</strong>
        <span class="status-pill status-${order.status}">${STATUS_LABELS[order.status]}</span></div>
        <ul>${order.items.map(item => `<li>${item.quantity} × ${item.dish_name} — ₹${item.subtotal}</li>`).join('')}</ul>
        <div><strong>Total: ₹${order.total_amount}</strong></div>
        <div class="muted">${new Date(order.created_at).toLocaleString()}</div></div>
    `).join('') : '<p class="muted">No orders match these filters.</p>';
    const pagination = document.getElementById('orders-pagination');
    if (Array.isArray(payload)) { pagination.innerHTML = ''; return; }
    pagination.innerHTML = `<button ${payload.previous ? '' : 'disabled'} data-page="${currentPage - 1}">Previous</button>
        <span>Page ${currentPage}</span><button ${payload.next ? '' : 'disabled'} data-page="${currentPage + 1}">Next</button>`;
    pagination.querySelectorAll('button:not([disabled])').forEach(button => button.addEventListener('click', () => {
        currentPage = parseInt(button.dataset.page, 10); loadOrders();
    }));
}

async function loadOrders() {
    const response = await fetch(`/api/orders/?${queryString()}`);
    if (response.ok) renderOrders(await response.json());
}

document.getElementById('order-filters').addEventListener('submit', event => {
    event.preventDefault(); currentPage = 1; loadOrders();
});
loadOrders();
setInterval(loadOrders, 7000);
