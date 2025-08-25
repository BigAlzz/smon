from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings


def months_elapsed_in_fy(start: date, end: date, as_of: date) -> int:
    """Return number of months elapsed in the financial year up to as_of (inclusive).
    Clamped within [start, end].
    """
    if as_of < start:
        return 0
    if as_of > end:
        as_of = end
    rd = relativedelta(as_of, start)
    return rd.years * 12 + rd.months + 1


def quarter_end_for(fin_year, as_of: date) -> date:
    """Compute the end date of the quarter in the given financial year that contains as_of.
    The financial year provides start_date and end_date.
    """
    start = fin_year.start_date
    end = fin_year.end_date
    m = months_elapsed_in_fy(start, end, as_of)
    if m <= 0:
        # Before FY starts, treat as first quarter end
        q_index = 1
    else:
        # ceil division by 3, clamp to 4
        q_index = min(4, (m + 2) // 3)
    q_start = start + relativedelta(months=(q_index - 1) * 3)
    q_end = q_start + relativedelta(months=3, days=-1)
    if q_end > end:
        q_end = end
    return q_end


def is_period_locked(fin_year, period_end: date, today: date | None = None) -> bool:
    """Return True if the quarter containing period_end is locked given settings.

    Lock policy (Phase 1): if enabled, edits are blocked when today is later than
    quarter_end + GRACE_DAYS.
    """
    cfg = getattr(settings, 'KPA_SETTINGS', {}).get('QUARTER_LOCK', {})
    enabled = cfg.get('ENABLED', False)
    grace_days = int(cfg.get('GRACE_DAYS', 14))
    if not enabled:
        return False
    if today is None:
        from django.utils import timezone
        today = timezone.now().date()
    q_end = quarter_end_for(fin_year, period_end)
    return today > (q_end + timedelta(days=grace_days))

