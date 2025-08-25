from datetime import date, timedelta
from django.test import TestCase
from django.conf import settings
from core.utils_time import is_period_locked, quarter_end_for
from core.models import FinancialYear


class QuarterLockTests(TestCase):
    def setUp(self):
        # SA FY: 1 Apr to 31 Mar next year in this project
        self.fy = FinancialYear.objects.create(
            year_code='FY 2024/25',
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_active=True,
        )
        # Ensure lock is enabled with 14 days
        settings.KPA_SETTINGS.setdefault('QUARTER_LOCK', {'ENABLED': True, 'GRACE_DAYS': 14})
        settings.KPA_SETTINGS['QUARTER_LOCK']['ENABLED'] = True
        settings.KPA_SETTINGS['QUARTER_LOCK']['GRACE_DAYS'] = 14

    def test_quarter_end_for_mid_april(self):
        q_end = quarter_end_for(self.fy, date(2024, 4, 15))
        self.assertEqual(q_end, date(2024, 6, 30))

    def test_is_period_locked_before_grace(self):
        # Period in Q1, testing just before grace expiry
        period_end = date(2024, 5, 31)
        q_end = quarter_end_for(self.fy, period_end)
        today = q_end + timedelta(days=13)
        self.assertFalse(is_period_locked(self.fy, period_end, today=today))

    def test_is_period_locked_after_grace(self):
        period_end = date(2024, 5, 31)
        q_end = quarter_end_for(self.fy, period_end)
        today = q_end + timedelta(days=15)
        self.assertTrue(is_period_locked(self.fy, period_end, today=today))

