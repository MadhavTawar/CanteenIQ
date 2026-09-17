# CanteenIQ Phase 2 Review Report

## Review objective

Review the Phase 2 enhancement work for correctness, regressions, security, user experience, and operational readiness. The application is a Django 6.1 + Django REST Framework 3.18 canteen ordering system using Django templates and vanilla JavaScript.

## Implemented changes

### Frontend

- Menu ordering no longer performs a full-page reload after checkout.
- Menu stock is re-fetched periodically and updated in place.
- Sold-out dishes disable quantity controls.
- Client-side menu search and category filtering were added.
- Student order history polls approximately every 7 seconds.
- Staff incoming orders and inventory poll approximately every 8 seconds.
- Staff forecast and daily sales sections use Chart.js bar charts by default.
- Raw forecast details remain available through a collapsible table.
- Staff can download daily sales as CSV.
- Shared in-page notifications were added:
  - Staff sees a popup when a newly detected student order arrives.
  - Students see a popup when a previously observed order changes status, including COMPLETED.
- The frontend handles both plain-array and paginated DRF list responses.

### API and backend

- Order history supports:
  - `status`
  - `start_date`
  - `end_date`
  - page-based pagination when filters or a page parameter are used
- Existing unfiltered order-list behavior remains a plain list for compatibility with the original frontend/tests.
- Daily sales CSV export is available to staff at:

  `GET /api/sales/?export=csv`

- OpenAPI schema and Swagger UI were added:
  - `/api/schema/`
  - `/api/docs/`
- Order placement has a DRF user throttle of 30 requests per minute.
- Inventory updates log a warning when quantity crosses from above 5 to 5 or below.
- Dockerfile and Docker Compose configuration were added for a Django + PostgreSQL demo stack.
- Existing stock safety remains in place: order placement uses `transaction.atomic()` and `select_for_update()`.

## Verification evidence

The following commands passed using the project virtual environment:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test core
```

Result:

- Django system check: no issues
- Test suite: 24 tests passed

The tests cover authentication/profile signals, inventory creation, order placement, stock decrement, overselling protection, order visibility, filtered pagination, CSV export, API docs availability, low-stock logging, role permissions, and forecasting behavior.

## Current data-refresh behavior

- Forecast endpoint defaults to tomorrow using the server's current date:
  `GET /api/forecast/`
- Sales endpoint defaults to today:
  `GET /api/sales/`
- Orders and inventory refresh through browser polling while the relevant page is open.
- The `Inventory.quantity_available` field is not automatically reset at midnight. Staff must enter the next day's prepared stock.
- Forecast and sales charts are loaded when the staff dashboard initializes. They are not currently date-aware polling loops that detect midnight and reload chart data automatically.
- Polling notifications are client-side. They only appear when the relevant staff or student page is open.
- WebSockets, push notifications, email, and SMS are not implemented.

## Review priorities for Claude

1. Check whether the compatibility behavior in `OrderViewSet.list()` is desirable. Unfiltered requests return a plain list, while filtered/page requests return DRF pagination metadata.
2. Check whether the 30-per-minute order throttle is appropriate for the expected user population and whether failed orders should count toward the limit.
3. Review authorization on all list, export, status-update, inventory, forecast, and documentation endpoints.
4. Review CSV output escaping, filename handling, date filtering, timezone behavior, and revenue calculation.
5. Review the notification implementation for duplicate notifications, multiple browser tabs, stale polling state, and XSS risks from interpolated API values.
6. Review whether CDN-hosted Chart.js is acceptable for the deployment environment or should be vendored/static-hosted.
7. Decide whether inventory needs a daily stock model or reset workflow instead of manual replacement.
8. Decide whether forecast and sales polling should reload automatically when the calendar date changes.
9. Review SQLite behavior versus PostgreSQL behavior for row locking and concurrency tests.
10. Review Docker production readiness. The current Compose command uses Django's development server and is intended for demos, not production deployment.

## Known intentional scope limits

- No payment gateway.
- No multi-canteen or multi-tenant model.
- No holidays, exams, or calendar effects in forecasting.
- No WebSockets or external notification infrastructure.
- No automatic inventory rollover at midnight.

## Suggested manual review flow

1. Start the app and log in in two browser windows, one as `staff` and one as `student1`.
2. Open `/staff/` in the staff window and `/` in the student window.
3. Place an order as the student and verify the staff popup, inventory decrement, and no full-page reload.
4. Open `/orders/` as the student and change the order status from `/staff/`; verify the student popup after polling.
5. Test menu search, category filtering, sold-out behavior, order filters, pagination, chart rendering, and CSV download.
6. Visit `/api/docs/` and inspect generated endpoint schemas and authorization behavior.
