function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}

const csrftoken = getCookie('csrftoken');
const cart = {};

function showBanner(message, type) {
    const banner = document.getElementById('status-banner');
    banner.innerHTML = `<div class="toast ${type}">${message}</div>`;
    setTimeout(() => { banner.innerHTML = ''; }, 5000);
}

function updateCartSummary() {
    let totalItems = 0;
    let totalPrice = 0;
    document.querySelectorAll('.dish-card').forEach(card => {
        const quantity = cart[card.dataset.dishId] || 0;
        totalItems += quantity;
        totalPrice += quantity * parseFloat(card.dataset.price);
        card.querySelector('.qty-value').textContent = quantity;
    });
    document.getElementById('cart-summary').textContent = totalItems
        ? `${totalItems} item(s) · ₹${totalPrice.toFixed(2)}` : 'Cart empty';
    document.getElementById('place-order-btn').disabled = totalItems === 0;
}

function applyStock(card, quantity) {
    const stock = card.querySelector('.stock');
    const dishId = card.dataset.dishId;
    stock.dataset.stock = quantity;
    stock.dataset.maxStock = quantity;
    stock.classList.toggle('low', quantity <= 5);
    stock.textContent = quantity === 0 ? 'Sold out' : `${quantity} left`;
    card.querySelectorAll('.qty-btn').forEach(button => { button.disabled = quantity === 0; });
    if ((cart[dishId] || 0) > quantity) cart[dishId] = quantity;
}

async function refreshStock() {
    const response = await fetch('/api/menu/');
    if (!response.ok) return;
    const payload = await response.json();
    const dishes = Array.isArray(payload) ? payload : payload.results;
    dishes.forEach(dish => {
        const card = document.querySelector(`[data-dish-id="${dish.id}"]`);
        if (card) applyStock(card, dish.quantity_available);
    });
    updateCartSummary();
}

function filterMenu() {
    const search = document.getElementById('menu-search').value.toLowerCase();
    const category = document.getElementById('menu-category').value;
    document.querySelectorAll('.dish-card').forEach(card => {
        const matchesName = card.querySelector('h3').textContent.toLowerCase().includes(search);
        card.hidden = !matchesName || (category && card.dataset.category !== category);
    });
}

document.querySelectorAll('.dish-card').forEach(card => {
    const dishId = card.dataset.dishId;
    card.querySelectorAll('.qty-btn').forEach(button => button.addEventListener('click', () => {
        const available = parseInt(card.querySelector('.stock').dataset.stock, 10);
        const current = cart[dishId] || 0;
        cart[dishId] = button.dataset.action === 'inc'
            ? Math.min(current + 1, available) : Math.max(current - 1, 0);
        updateCartSummary();
    }));
    applyStock(card, parseInt(card.querySelector('.stock').dataset.stock, 10));
});

document.getElementById('menu-search').addEventListener('input', filterMenu);
document.getElementById('menu-category').addEventListener('change', filterMenu);
document.getElementById('place-order-btn').addEventListener('click', async () => {
    const items = Object.entries(cart).filter(([, quantity]) => quantity > 0)
        .map(([dish, quantity]) => ({ dish: parseInt(dish, 10), quantity }));
    if (!items.length) return;
    const response = await fetch('/api/orders/', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken},
        body: JSON.stringify({items}),
    });
    if (response.status === 201) {
        Object.keys(cart).forEach(key => delete cart[key]);
        updateCartSummary();
        await refreshStock();
        showBanner('Order placed! Track it under "My Orders".', 'success');
    } else {
        const error = await response.json();
        showBanner(error.detail || 'Could not place order.', 'error');
    }
});

updateCartSummary();
refreshStock();
setInterval(refreshStock, 8000);
