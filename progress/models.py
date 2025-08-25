"""
Progress and tracking models for KPA Performance Monitoring App

This module contains models for tracking progress against targets:
Target, ProgressUpdate, CostLine with calculated fields for RAG status,
variance calculations, and forecasting.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

from core.models import BaseModel, OperationalPlanItem


class Target(BaseModel):
    """
    Represents a measurable target for an operational plan item
    """
    UNIT_CHOICES = [
        ('NUMBER', 'Number'),
        ('PERCENTAGE', 'Percentage'),
        ('CURRENCY', 'Currency (ZAR)'),
        ('RATIO', 'Ratio'),
        ('DAYS', 'Days'),
        ('HOURS', 'Hours'),
        ('PEOPLE', 'People'),
        ('DOCUMENTS', 'Documents'),
        ('EVENTS', 'Events'),
        ('OTHER', 'Other'),
    ]

    PERIODICITY_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUAL', 'Annual'),
        ('MILESTONE', 'Milestone-based'),
    ]

    plan_item = models.ForeignKey(
        OperationalPlanItem,
        on_delete=models.CASCADE,
        related_name='targets'
    )

    # Target definition
    name = models.CharField(
        max_length=200,
        help_text="Name/description of this target"
    )
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Target value to achieve"
    )
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default='NUMBER'
    )
    baseline = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Starting baseline value"
    )

    # Timing and periodicity
    due_date = models.DateField(
        help_text="When this target should be achieved"
    )
    periodicity = models.CharField(
        max_length=20,
        choices=PERIODICITY_CHOICES,
        default='ANNUAL'
    )

    # RAG thresholds (configurable per target)
    green_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('95.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Minimum percentage for Green status"
    )
    amber_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('80.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Minimum percentage for Amber status"
    )

    # Tolerance bands
    positive_tolerance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Acceptable positive variance percentage"
    )
    negative_tolerance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text="Acceptable negative variance percentage"
    )

    is_cumulative = models.BooleanField(
        default=True,
        help_text="Whether progress accumulates over time"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['plan_item', 'due_date']
        verbose_name = "Target"
        verbose_name_plural = "Targets"

    def __str__(self):
        return f"{self.name} - {self.value} {self.get_unit_display()}"

    def is_overdue_for_update(self):
        """Check if this target is overdue for a progress update"""
        if not self.due_date:
            return False

        # Get the latest progress update
        latest_update = self.progress_updates.filter(is_active=True).order_by('-period_end').first()

        if not latest_update:
            # No updates yet, check if we're past the first expected update period
            return date.today() > self.due_date

        # Check if we need an update based on periodicity
        if self.periodicity == 'monthly':
            expected_next_update = latest_update.period_end + relativedelta(months=1)
        elif self.periodicity == 'quarterly':
            expected_next_update = latest_update.period_end + relativedelta(months=3)
        elif self.periodicity == 'annually':
            expected_next_update = latest_update.period_end + relativedelta(years=1)
        else:
            return False

        return date.today() > expected_next_update

    def get_current_period(self):
        """Get the current reporting period for this target"""
        today = date.today()

        if self.periodicity == 'monthly':
            start = today.replace(day=1)
            end = (start + relativedelta(months=1)) - timedelta(days=1)
            name = start.strftime('%B %Y')
        elif self.periodicity == 'quarterly':
            quarter = (today.month - 1) // 3 + 1
            start = date(today.year, (quarter - 1) * 3 + 1, 1)
            end = (start + relativedelta(months=3)) - timedelta(days=1)
            name = f"Q{quarter} {today.year}"
        elif self.periodicity == 'annually':
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)
            name = str(today.year)
        else:
            start = today
            end = today
            name = today.strftime('%Y-%m-%d')

        return {
            'start': start,
            'end': end,
            'name': name
        }

    def get_rag_status(self):
        """Get RAG (Red/Amber/Green) status based on latest progress"""
        latest_update = self.progress_updates.filter(is_active=True).order_by('-period_end').first()

        if not latest_update:
            return 'GREY'

        actual = latest_update.actual_value

        # Compare against thresholds
        if actual >= self.green_threshold:
            return 'GREEN'
        elif actual >= self.amber_threshold:
            return 'AMBER'
        else:
            return 'RED'

    def get_progress_percentage(self):
        """Get progress as a percentage of target"""
        latest_update = self.progress_updates.filter(is_active=True).order_by('-period_end').first()

        if not latest_update or self.value == 0:
            return 0

        return min(100, (latest_update.actual_value / self.value) * 100)

    @property
    def ytd_target(self):
        """Calculate year-to-date target based on current date and periodicity.
        Safe when fields are incomplete (e.g., admin add form) by returning 0.
        """
        today = date.today()
        if self.value is None:
            return Decimal('0.00')
        if not self.due_date:
            return Decimal('0.00')
        if today > self.due_date:
            return self.value or Decimal('0.00')

        if self.periodicity == 'ANNUAL':
            # Calculate proportional target based on days elapsed
            start_of_year = date(today.year, 4, 1)  # SA financial year starts April 1
            end_of_year = date(today.year + 1, 3, 31)

            if today < start_of_year:
                return Decimal('0.00')

            days_elapsed = (today - start_of_year).days
            total_days = (end_of_year - start_of_year).days
            proportion = Decimal(str(days_elapsed / total_days))

            return self.value * proportion

        elif self.periodicity == 'QUARTERLY':
            # Calculate based on completed quarters
            quarters_elapsed = ((today.month - 4) // 3) + 1 if today.month >= 4 else ((today.month + 8) // 3) + 1
            return (self.value / 4) * min(quarters_elapsed, 4)

        elif self.periodicity == 'MONTHLY':
            # Calculate based on completed months
            if today.month >= 4:
                months_elapsed = today.month - 3
            else:
                months_elapsed = today.month + 9
            return (self.value / 12) * min(months_elapsed, 12)

        return self.value

    def get_latest_progress(self):
        """Get the most recent progress update"""
        return self.progress_updates.filter(is_active=True).order_by('-period_end').first()

    def calculate_rag_status(self, actual_value=None):
        """Calculate RAG status based on actual vs target"""
        if actual_value is None:
            latest_progress = self.get_latest_progress()
            if not latest_progress:
                return 'GREY'  # No data
            actual_value = latest_progress.actual_value

        ytd_target = self.ytd_target
        if ytd_target == 0:
            return 'GREY'

        percentage = (actual_value / ytd_target) * 100

        if percentage >= self.green_threshold:
            return 'GREEN'
        elif percentage >= self.amber_threshold:
            return 'AMBER'
        else:
            return 'RED'


class ProgressUpdate(BaseModel):
    """
    Represents a progress update against a target for a specific period
    """
    PERIOD_TYPE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUAL', 'Annual'),
        ('MILESTONE', 'Milestone'),
    ]

    RISK_RATING_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]

    target = models.ForeignKey(
        Target,
        on_delete=models.CASCADE,
        related_name='progress_updates'
    )

    # Period information
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default='MONTHLY'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    period_name = models.CharField(
        max_length=50,
        help_text="e.g., 'April 2024', 'Q1 2024/25'"
    )

    # Progress data
    actual_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Actual achievement for this period"
    )

    # Narrative and evidence
    narrative = models.TextField(
        help_text="Explanation of progress, challenges, achievements"
    )
    evidence_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="URLs to supporting evidence/documents"
    )

    # Evidence file uploads
    evidence_files = models.JSONField(
        default=list,
        blank=True,
        help_text="Uploaded evidence files metadata"
    )

    # Risk and issues
    risk_rating = models.CharField(
        max_length=20,
        choices=RISK_RATING_CHOICES,
        default='LOW'
    )
    issues = models.TextField(
        blank=True,
        help_text="Current issues or challenges"
    )
    corrective_actions = models.TextField(
        blank=True,
        help_text="Actions being taken to address issues"
    )

    # Forecasting
    forecast_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated final achievement (EAC - Estimate at Completion)"
    )
    forecast_confidence = models.CharField(
        max_length=20,
        choices=[
            ('HIGH', 'High Confidence'),
            ('MEDIUM', 'Medium Confidence'),
            ('LOW', 'Low Confidence'),
        ],
        default='MEDIUM',
        blank=True
    )

    # Status tracking
    is_submitted = models.BooleanField(
        default=False,
        help_text="Whether this update has been submitted"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(
        default=False,
        help_text="Whether this update has been approved by senior manager"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_progress_updates'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    approval_comments = models.TextField(
        blank=True,
        help_text="Comments from the approver"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-period_end', 'target']
        verbose_name = "Progress Update"
        verbose_name_plural = "Progress Updates"
        unique_together = ['target', 'period_start', 'period_end']

    def __str__(self):
        return f"{self.target.name} - {self.period_name}: {self.actual_value}"

    def save(self, *args, **kwargs):
        if self.is_submitted and not self.submitted_at:
            self.submitted_at = timezone.now()
        if self.is_approved and not self.approved_at:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def variance_absolute(self):
        """Calculate absolute variance from target"""
        ytd_target = self.target.ytd_target
        return self.actual_value - ytd_target

    @property
    def variance_percentage(self):
        """Calculate percentage variance from target"""
        ytd_target = self.target.ytd_target
        if ytd_target == 0:
            return Decimal('0.00')
        return ((self.actual_value - ytd_target) / ytd_target) * 100

    @property
    def rag_status(self):
        """Get RAG status for this progress update"""
        return self.target.calculate_rag_status(self.actual_value)

    @property
    def percentage_complete(self):
        """Calculate percentage completion against target"""
        ytd_target = self.target.ytd_target
        if ytd_target == 0:
            return Decimal('0.00')
        return (self.actual_value / ytd_target) * 100

    def is_evidence_required(self):
        """Check if evidence is required based on RAG status and duration"""
        if self.rag_status in ['RED', 'AMBER']:
            # Check if this status has persisted for the required number of months
            evidence_months = getattr(settings, 'KPA_SETTINGS', {}).get('EVIDENCE_REQUIRED_AFTER_MONTHS', 2)
            cutoff_date = self.period_end - relativedelta(months=evidence_months)

            # Count consecutive RED/AMBER updates
            consecutive_updates = ProgressUpdate.objects.filter(
                target=self.target,
                period_end__gte=cutoff_date,
                period_end__lte=self.period_end,
                is_active=True
            ).order_by('period_end')

            red_amber_count = 0
            for update in consecutive_updates:
                if update.rag_status in ['RED', 'AMBER']:
                    red_amber_count += 1
                else:
                    red_amber_count = 0  # Reset if we hit a GREEN

            return red_amber_count >= evidence_months
        return False


class EvidenceFile(BaseModel):
    """
    Model for storing uploaded evidence files
    """
    progress_update = models.ForeignKey(
        ProgressUpdate,
        on_delete=models.CASCADE,
        related_name='uploaded_evidence'
    )

    file = models.FileField(
        upload_to='evidence/%Y/%m/',
        help_text="Evidence file (PDF, Excel, Word, Image, etc.)"
    )

    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename when uploaded"
    )

    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )

    file_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional description of the evidence"
    )

    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        help_text="User who uploaded this file"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the file was uploaded"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this evidence file is active"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Evidence File"
        verbose_name_plural = "Evidence Files"

    def __str__(self):
        return f"{self.original_filename} - {self.progress_update}"

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_type.startswith('image/')

    @property
    def is_pdf(self):
        """Check if file is a PDF"""
        return self.file_type == 'application/pdf'

    @property
    def is_excel(self):
        """Check if file is an Excel file"""
        return self.file_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]

    @property
    def is_word(self):
        """Check if file is a Word document"""
        return self.file_type in [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]

    @property
    def file_icon(self):
        """Return appropriate Bootstrap icon for file type"""
        if self.is_image:
            return 'bi-image'
        elif self.is_pdf:
            return 'bi-file-earmark-pdf'
        elif self.is_excel:
            return 'bi-file-earmark-excel'
        elif self.is_word:
            return 'bi-file-earmark-word'
        else:
            return 'bi-file-earmark'


class CostLine(BaseModel):
    """
    Represents cost tracking for operational plan items
    """
    COST_TYPE_CHOICES = [
        ('INPUT', 'Input Cost'),
        ('OUTPUT', 'Output Cost'),
        ('OPERATIONAL', 'Operational Cost'),
        ('CAPITAL', 'Capital Cost'),
    ]

    FUNDING_SOURCE_CHOICES = [
        ('GOVERNMENT', 'Government Grant'),
        ('DONOR', 'Donor Funding'),
        ('INTERNAL', 'Internal Revenue'),
        ('OTHER', 'Other Sources'),
    ]

    plan_item = models.ForeignKey(
        OperationalPlanItem,
        on_delete=models.CASCADE,
        related_name='cost_lines'
    )

    # Cost details
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        default='INPUT'
    )
    description = models.CharField(
        max_length=200,
        help_text="Description of this cost item"
    )

    # Financial amounts
    budgeted_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Originally budgeted amount"
    )
    committed_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount committed/contracted"
    )
    actual_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Actual amount spent"
    )

    # Period and timing
    cost_period_start = models.DateField()
    cost_period_end = models.DateField()

    # Funding and classification
    funding_source = models.CharField(
        max_length=20,
        choices=FUNDING_SOURCE_CHOICES,
        default='GOVERNMENT'
    )

    # Additional tracking
    purchase_order_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="PO or reference number"
    )
    supplier_vendor = models.CharField(
        max_length=200,
        blank=True,
        help_text="Supplier or vendor name"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['plan_item', 'cost_period_start']
        verbose_name = "Cost Line"
        verbose_name_plural = "Cost Lines"

    def __str__(self):
        return f"{self.description} - R{self.budgeted_amount:,.2f}"

    @property
    def variance_amount(self):
        """Calculate variance between budgeted and actual spend"""
        return self.actual_spend - self.budgeted_amount

    @property
    def variance_percentage(self):
        """Calculate percentage variance"""
        if self.budgeted_amount == 0:
            return Decimal('0.00')
        return (self.variance_amount / self.budgeted_amount) * 100

    @property
    def commitment_percentage(self):
        """Calculate percentage of budget committed"""
        if self.budgeted_amount == 0:
            return Decimal('0.00')
        return (self.committed_amount / self.budgeted_amount) * 100

    @property
    def spend_percentage(self):
        """Calculate percentage of budget spent"""
        if self.budgeted_amount == 0:
            return Decimal('0.00')
        return (self.actual_spend / self.budgeted_amount) * 100

    @property
    def remaining_budget(self):
        """Calculate remaining budget"""
        return self.budgeted_amount - self.actual_spend

    def is_overspent(self):
        """Check if this cost line is over budget"""
        return self.actual_spend > self.budgeted_amount

    def get_spend_status(self):
        """Get spend status based on percentage spent"""
        spend_pct = self.spend_percentage
        if spend_pct >= 100:
            return 'OVERSPENT' if self.is_overspent() else 'FULLY_SPENT'
        elif spend_pct >= 80:
            return 'HIGH_SPEND'
        elif spend_pct >= 50:
            return 'MODERATE_SPEND'
        else:
            return 'LOW_SPEND'
