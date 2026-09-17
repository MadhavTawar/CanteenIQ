async function loadOrders() {
    const res = await fetch('/api/orders/');
    const orders = await res.json();
    const container = document.getElementById('orders-list');

    if (!orders.length) {
        container.innerHTML = '<p class="muted">No orders yet — head to the menu to place one.</p>';
        return;
    }

    container.innerHTML = orders.map(order => `
        <div class="order-card">
            <div class="order-header">
                <strong>Order #${order.id}</strong>
                <span class="status-pill status-${order.status}">${order.status}</span>
            </div>
            <ul>
                ${order.items.map(i => `<li>${i.quantity} × ${i.dish_name} — ₹${i.subtotal}</li>`).join('')}
            </ul>
            <div><strong>Total: ₹${order.total_amount}</strong></div>
            <div class="muted">${new Date(order.created_at).toLocaleString()}</div>
        </div>
    `).join('');
}

loadOrders();
