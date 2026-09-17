function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}
const csrftoken = getCookie('csrftoken');

const cart = {}; // { dishId: qty }

function updateCartSummary() {
    const dishCards = document.querySelectorAll('.dish-card');
    let totalItems = 0;
    let totalPrice = 0;

    dishCards.forEach(card => {
        const dishId = card.dataset.dishId;
        const price = parseFloat(card.dataset.price);
        const qty = cart[dishId] || 0;
        if (qty > 0) {
            totalItems += qty;
            totalPrice += qty * price;
        }
    });

    const summary = document.getElementById('cart-summary');
    const placeBtn = document.getElementById('place-order-btn');
    if (totalItems === 0) {
        summary.textContent = 'Cart empty';
        placeBtn.disabled = true;
    } else {
        summary.textContent = `${totalItems} item(s) · ₹${totalPrice.toFixed(2)}`;
        placeBtn.disabled = false;
    }
}

function showBanner(message, type) {
    const banner = document.getElementById('status-banner');
    banner.innerHTML = `<div class="toast ${type}">${message}</div>`;
    setTimeout(() => { banner.innerHTML = ''; }, 5000);
}

document.querySelectorAll('.dish-card').forEach(card => {
    const dishId = card.dataset.dishId;
    const qtyValueEl = card.querySelector('.qty-value');
    const stockEl = card.querySelector('.stock');
    const maxStock = parseInt(stockEl.dataset.stock, 10);

    card.querySelectorAll('.qty-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            let qty = cart[dishId] || 0;
            if (btn.dataset.action === 'inc' && qty < maxStock) {
                qty += 1;
            } else if (btn.dataset.action === 'dec' && qty > 0) {
                qty -= 1;
            }
            cart[dishId] = qty;
            qtyValueEl.textContent = qty;
            updateCartSummary();
        });
    });

    if (maxStock === 0) {
        stockEl.classList.add('low');
        stockEl.textContent = 'Sold out';
        card.querySelectorAll('.qty-btn').forEach(b => b.disabled = true);
    } else if (maxStock <= 5) {
        stockEl.classList.add('low');
    }
});

document.getElementById('place-order-btn').addEventListener('click', async () => {
    const items = Object.entries(cart)
        .filter(([, qty]) => qty > 0)
        .map(([dish, qty]) => ({ dish: parseInt(dish, 10), quantity: qty }));

    if (items.length === 0) return;

    const res = await fetch('/api/orders/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({ items }),
    });

    if (res.status === 201) {
        showBanner('Order placed! Track it under "My Orders".', 'success');
        Object.keys(cart).forEach(k => delete cart[k]);
        document.querySelectorAll('.qty-value').forEach(el => el.textContent = '0');
        updateCartSummary();
        setTimeout(() => window.location.reload(), 1500); // refresh stock counts
    } else {
        const err = await res.json();
        showBanner(err.detail || 'Could not place order.', 'error');
    }
});

updateCartSummary();
