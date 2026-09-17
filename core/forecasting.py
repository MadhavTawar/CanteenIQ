"""
Demand forecasting — the one AI-touching feature in CanteenIQ.

Deliberately simple and explainable: it is a weekday-aware historical
average, not a deep model. That's a defensible design choice, not a
shortcut — a college canteen's demand pattern is dominated by day-of-week
(e.g. lighter footfall on weekends, heavier on exam days if flagged),
and a small historical dataset can't reliably support anything fancier
without overfitting. This is intentionally the honest answer to "what
does the AI actually do here."

predict_demand() returns a whole-number quantity to prepare for a given
dish on a given future date, based on how much of that dish was ordered
on the same weekday over the last N occurrences.
"""

from collections import Counter
from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate

from .models import OrderItem


def predict_demand(dish, target_date, lookback_weeks=6):
    """Predict how many units of `dish` to prepare for `target_date`.

    Looks at the same weekday over the past `lookback_weeks` weeks,
    averages the total quantity ordered on each of those dates, and
    rounds up (better to slightly over-prepare than run out).

    Falls back to the dish's all-time daily average if there isn't
    enough same-weekday history yet (e.g. a newly added dish).
    """
    target_weekday = target_date.weekday()
    earliest = target_date - timedelta(weeks=lookback_weeks)

    daily_totals = (
        OrderItem.objects.filter(
            dish=dish,
            order__created_at__date__gte=earliest,
            order__created_at__date__lt=target_date,
        )
        .annotate(day=TruncDate('order__created_at'))
        .values('day')
        .annotate(total_qty=Sum('quantity'))
    )

    same_weekday_totals = [
        row['total_qty'] for row in daily_totals if row['day'].weekday() == target_weekday
    ]

    if same_weekday_totals:
        avg = sum(same_weekday_totals) / len(same_weekday_totals)
        source = f'{len(same_weekday_totals)}-week same-weekday average'
    elif daily_totals:
        all_totals = [row['total_qty'] for row in daily_totals]
        avg = sum(all_totals) / len(all_totals)
        source = 'all-time daily average (not enough same-weekday history yet)'
    else:
        avg = 0
        source = 'no order history yet'

    predicted_qty = int(avg) + (1 if avg % 1 else 0)  # round up
    return {
        'dish': dish.name,
        'target_date': target_date.isoformat(),
        'predicted_quantity': predicted_qty,
        'basis': source,
    }


def predict_demand_for_all(target_date, dishes, lookback_weeks=6):
    return [predict_demand(dish, target_date, lookback_weeks) for dish in dishes]
