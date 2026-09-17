# CanteenIQ

A full-stack canteen management system for a college food service, built with Django and Django REST Framework. Covers menu management, ordering, inventory, and billing — plus one deliberately small AI-touching feature: next-day demand forecasting.

## Why this project exists

College canteens routinely over-prepare or under-prepare food because nobody tracks what actually got ordered on, say, every past Tuesday. That's a real, small, well-scoped problem — which is why the AI here is a simple weekday-average forecast, not a headline feature. The system is a full-stack ordering platform first; forecasting is one module inside it.

## Architecture

```text
config/          Django project settings, root urls
core/
  models.py      Profile, Dish, Inventory, Order, OrderItem
  serializers.py DRF serializers
  views_api.py   DRF viewsets + forecast/sales endpoints
  views.py       Template views (menu, orders, staff dashboard, signup)
  permissions.py Role-based DRF permission classes
  forecasting.py The demand-forecasting logic (see below)
  signals.py     Auto-create Profile (on User) and Inventory (on Dish)
  admin.py       Django admin registrations
  tests.py       24 tests: auth, ordering, concurrency, forecasting, Phase 2 API behavior
  management/commands/seed_demo.py   Demo data + 8 weeks of order history
templates/       Django templates (base + core + registration)
static/          CSS + vanilla JS (no frontend framework)
Dockerfile       Container image for the Django app
docker-compose.yml  Django + PostgreSQL demo stack
```

### Data model

- **Profile** — extends Django's built-in `User` with a `role` (STUDENT / STAFF) instead of a custom User model. Keeps auth simple; role checks live in `permissions.py`.
- **Dish** — menu item with category and price.
- **Inventory** — one-to-one with Dish; today's remaining quantity.
- **Order / OrderItem** — a student's order and its line items. `OrderItem` has a `unique_together` constraint on `(order, dish)` so a dish can't appear twice as separate lines on the same order.

### Concurrency safety (the thing to walk through if asked)

Order placement (`OrderViewSet.create`) wraps the whole operation in `transaction.atomic()` and takes `select_for_update()` on the `Inventory` row for each dish before checking stock. If two students try to order the last portion of the same dish at the same instant, the second request blocks on the row lock, re-reads the now-updated quantity after the first commits, and fails cleanly with a 409 instead of both succeeding and driving the count negative. `test_cannot_order_more_than_available_stock` and `test_failed_order_does_not_create_a_partial_order_row` in `core/tests.py` cover this.

### Role-based access

- `IsStaffOrReadOnly` — anyone logged in can view the menu; only staff can create/edit dishes.
- `IsStaffRole` — inventory, forecast, and sales endpoints are staff-only.
- `IsOwnerOrStaff` — students can only see/update their own orders; staff can see and update all of them.

### The forecasting feature — and why it's simple

`core/forecasting.py` predicts tomorrow's quantity per dish by averaging how much was ordered on the same weekday over the last 6 weeks (falling back to an all-time average, or 0, if there isn't enough history yet). That's the whole model — no neural net, no external ML library.

This is a deliberate choice, worth stating plainly in an interview: a single canteen's order volume is small, dominated by day-of-week patterns, and doesn't have enough data to safely support anything heavier without overfitting. A simple, explainable average is the *correct* engineering choice here, not a cut corner — and it's honestly the only "AI" claim in the whole project.

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # creates demo users, dishes, and 8 weeks of order history
python manage.py runserver
```

For a Postgres-backed demo with one command, use Docker Compose instead:

```bash
docker compose up --build
```

Phase 2 adds 8-second polling to the student orders and staff dashboard pages, in-place menu stock updates after ordering, client-side menu search/category filters, Chart.js forecast and sales charts, and paginated/date/status-filtered order history. Sales can be downloaded by staff from the dashboard or with `GET /api/sales/?export=csv`. Interactive OpenAPI documentation is available at `/api/docs/`.

Demo logins (from `seed_demo`):

- Staff: `staff` / `staff12345`
- Students: `student1` / `student2` / `student3`, password `student12345`

Visit `/` for the menu (student view), `/staff/` for the staff dashboard, `/admin/` for the Django admin.

### Using PostgreSQL instead of the SQLite dev default

The project defaults to SQLite for a zero-setup local run. To match the resume claim of PostgreSQL, set:

```bash
export USE_POSTGRES=true
export DB_NAME=canteeniq DB_USER=canteeniq DB_PASSWORD=canteeniq DB_HOST=localhost DB_PORT=5432
python manage.py migrate
```

## Tests

```bash
python manage.py test core
```

24 tests covering: default role assignment on signup, auto-provisioned inventory rows, order placement and stock decrement, the overselling/concurrency guard, order visibility isolation between students, filtered/paginated order history, CSV sales export, API docs availability, low-stock notification logging, staff-vs-student permission boundaries on every endpoint, anonymous-access rejection, and the forecasting logic (same-weekday average, fallback to all-time average, zero-history case).

## Honest gaps (things not implemented, on purpose, to keep scope tight)

- No payment gateway — billing computes totals but doesn't process payment.
- No WebSockets for live order-status push; the frontend uses lightweight 7–8 second polling for the student orders and staff dashboard views.
- Forecasting doesn't account for holidays/exam schedules — would be the natural next feature to add.
