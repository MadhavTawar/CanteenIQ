function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}
const csrftoken = getCookie('csrftoken');
const STATUS_CHOICES = ['PLACED', 'PREPARING', 'READY', 'COMPLETED', 'CANCELLED'];

async function loadIncomingOrders() {
    const res = await fetch('/api/orders/');
    const orders = await res.json();
    const container = document.getElementById('incoming-orders');

    const active = orders.filter(o => !['COMPLETED', 'CANCELLED'].includes(o.status));
    if (!active.length) {
        container.innerHTML = '<p class="muted">No active orders.</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <tr><th>#</th><th>Student</th><th>Items</th><th>Total</th><th>Status</th></tr>
            ${active.map(o => `
                <tr>
                    <td>${o.id}</td>
                    <td>${o.student_username}</td>
                    <td>${o.items.map(i => `${i.quantity}×${i.dish_name}`).join(', ')}</td>
                    <td>₹${o.total_amount}</td>
                    <td>
                        <select class="status-select" data-order-id="${o.id}">
                            ${STATUS_CHOICES.map(s => `<option value="${s}" ${s === o.status ? 'selected' : ''}>${s}</option>`).join('')}
                        </select>
                    </td>
                </tr>
            `).join('')}
        </table>
    `;

    container.querySelectorAll('.status-select').forEach(select => {
        select.addEventListener('change', async () => {
            await fetch(`/api/orders/${select.dataset.orderId}/set_status/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify({ status: select.value }),
            });
        });
    });
}

async function loadInventory() {
    const res = await fetch('/api/inventory/');
    const inventory = await res.json();
    const container = document.getElementById('inventory-list');

    container.innerHTML = `
        <table>
            <tr><th>Dish</th><th>Available</th><th>Update</th></tr>
            ${inventory.map(inv => `
                <tr>
                    <td>${inv.dish_name}</td>
                    <td>${inv.quantity_available}</td>
                    <td>
                        <input type="number" min="0" value="${inv.quantity_available}"
                               data-inv-id="${inv.id}" class="qty-input" style="width:70px">
                    </td>
                </tr>
            `).join('')}
        </table>
    `;

    container.querySelectorAll('.qty-input').forEach(input => {
        input.addEventListener('change', async () => {
            await fetch(`/api/inventory/${input.dataset.invId}/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify({ quantity_available: parseInt(input.value, 10) }),
            });
        });
    });
}

async function loadForecast() {
    const res = await fetch('/api/forecast/');
    const forecast = await res.json();
    const container = document.getElementById('forecast-list');

    container.innerHTML = `
        <table>
            <tr><th>Dish</th><th>Predicted qty (tomorrow)</th><th>Basis</th></tr>
            ${forecast.map(f => `
                <tr><td>${f.dish}</td><td>${f.predicted_quantity}</td><td class="muted">${f.basis}</td></tr>
            `).join('')}
        </table>
    `;
}

async function loadSales() {
    const res = await fetch('/api/sales/');
    const data = await res.json();
    const container = document.getElementById('sales-summary');

    container.innerHTML = `
        <p><strong>Revenue today: ₹${data.revenue}</strong></p>
        <table>
            <tr><th>Dish</th><th>Units sold</th></tr>
            ${data.per_dish.map(d => `<tr><td>${d.dish__name}</td><td>${d.units_sold}</td></tr>`).join('')}
        </table>
    `;
}

loadIncomingOrders();
loadInventory();
loadForecast();
loadSales();
