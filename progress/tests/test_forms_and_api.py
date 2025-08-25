from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from accounts.models import UserProfile
from core.models import FinancialYear, KPA, OperationalPlanItem
from progress.models import Target, ProgressUpdate
from progress.forms import ProgressUpdateForm


class EvidenceParsingTests(TestCase):
    def setUp(self):
        self.fy = FinancialYear.objects.create(
            year_code='FY 2024/25',
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_active=True,
        )
        owner = User.objects.create_user('owner', password='x', first_name='O', last_name='Wner')
        self.kpa = KPA.objects.create(
            title='Test KPA', description='Desc', owner=owner,
            strategic_objective='SO', financial_year=self.fy, order=1,
        )
        self.plan = OperationalPlanItem.objects.create(
            kpa=self.kpa, output='Out', activities=[], target_description='TD',
            indicator='Ind', inputs=[], input_cost=0, output_cost=0,
            timeframe='FY', start_date=self.fy.start_date, end_date=self.fy.end_date,
            budget_programme='Prog', responsible_officer='Prog Manager',
        )
        self.target = Target.objects.create(
            plan_item=self.plan, name='T1', value=100, unit='NUMBER', baseline=0,
            due_date=self.fy.end_date, periodicity='ANNUAL', is_cumulative=True,
        )

    def test_evidence_urls_parsing_in_form(self):
        form = ProgressUpdateForm(data={
            'target': self.target.id,
            'period_type': 'MONTHLY',
            'period_start': '2024-04-01',
            'period_end': '2024-04-30',
            'period_name': 'April 2024',
            'actual_value': '10',
            'narrative': 'Test',
            'evidence_urls': 'http://a\n\n http://b ',
            'risk_rating': 'LOW',
            'is_submitted': 'false',
        }, plan_item=self.plan)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['evidence_urls'], ['http://a', 'http://b'])


class DraftAutosaveApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('pm', password='x', first_name='Prog', last_name='Manager')
        self.profile = UserProfile.objects.create(
            user=self.user, job_title='PM', department='D',
            primary_role='PROGRAMME_MANAGER'
        )
        self.fy = FinancialYear.objects.create(
            year_code='FY 2024/25',
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_active=True,
        )
        owner = User.objects.create_user('owner', password='x', first_name='O', last_name='Wner')
        self.kpa = KPA.objects.create(
            title='Test KPA', description='Desc', owner=owner,
            strategic_objective='SO', financial_year=self.fy, order=1,
        )
        self.plan = OperationalPlanItem.objects.create(
            kpa=self.kpa, output='Out', activities=[], target_description='TD',
            indicator='Ind', inputs=[], input_cost=0, output_cost=0,
            timeframe='FY', start_date=self.fy.start_date, end_date=self.fy.end_date,
            budget_programme='Prog', responsible_officer='Prog Manager',
        )
        self.target = Target.objects.create(
            plan_item=self.plan, name='T1', value=100, unit='NUMBER', baseline=0,
            due_date=self.fy.end_date, periodicity='ANNUAL', is_cumulative=True,
        )
        # RBAC: profile.can_edit_plan_item -> responsible_officer contains full name
        self.plan.responsible_officer = self.user.get_full_name()
        self.plan.save()
        settings.KPA_SETTINGS.setdefault('QUARTER_LOCK', {'ENABLED': False, 'GRACE_DAYS': 14})
        settings.KPA_SETTINGS['QUARTER_LOCK']['ENABLED'] = False

    def test_autosave_creates_draft(self):
        self.client.login(username='pm', password='x')
        url = '/api/progress-updates/draft/'
        payload = {
            'target': str(self.target.id),
            'period_type': 'MONTHLY',
            'period_start': '2024-04-01',
            'period_end': '2024-06-30',
            'period_name': 'Q1 2024/25',
            'actual_value': '5',
            'narrative': 'Init',
            'evidence_urls': 'http://a\nhttp://b',
            'is_submitted': 'false'
        }
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ProgressUpdate.objects.count(), 1)
        draft = ProgressUpdate.objects.first()
        self.assertFalse(draft.is_submitted)
        self.assertEqual(draft.evidence_urls, ['http://a', 'http://b'])

    def test_autosave_upserts_draft(self):
        self.client.login(username='pm', password='x')
        url = '/api/progress-updates/draft/'
        base = {
            'target': str(self.target.id),
            'period_type': 'MONTHLY',
            'period_start': '2024-04-01',
            'period_end': '2024-06-30',
            'period_name': 'Q1 2024/25',
            'is_submitted': 'false'
        }
        resp = self.client.post(url, data={**base, 'actual_value': '5', 'narrative': 'A'})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url, data={**base, 'actual_value': '7', 'narrative': 'B'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ProgressUpdate.objects.count(), 1)
        draft = ProgressUpdate.objects.first()
        self.assertEqual(str(draft.actual_value), '7')
        self.assertEqual(draft.narrative, 'B')

