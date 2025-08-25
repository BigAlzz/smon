"""
Core models for KPA Performance Monitoring App

This module contains the fundamental models that represent the core entities
of the GCRA Operational Plan structure: FinancialYear, KPA, and OperationalPlanItem.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class BaseModel(models.Model):
    """
    Abstract base model with common fields for all models
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )

    class Meta:
        abstract = True


class FinancialYear(BaseModel):
    """
    Represents a financial year for the operational plan
    """
    year_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="e.g., 'FY 2024/25'"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(
        default=False,
        help_text="Only one financial year can be active at a time"
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Financial Year"
        verbose_name_plural = "Financial Years"

    def __str__(self):
        return self.year_code

    def save(self, *args, **kwargs):
        # Ensure only one active financial year
        if self.is_active:
            FinancialYear.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class OrgUnit(BaseModel):
    """Organizational unit (Chief Directorate / Directorate / Sub-Directorate)"""
    UNIT_TYPE_CHOICES = [
        ('CEO_OFFICE', 'CEO Office'),
        ('CHIEF_DIRECTORATE', 'Chief Directorate'),
        ('DIRECTORATE', 'Directorate'),
        ('SUB_DIRECTORATE', 'Sub-Directorate'),
    ]
    name = models.CharField(max_length=200, unique=True)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPE_CHOICES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['unit_type', 'name']
        verbose_name = 'Organizational Unit'
        verbose_name_plural = 'Organizational Units'

    def __str__(self):
        return f"{self.name} ({self.get_unit_type_display()})"


class KPA(BaseModel):
    """
    Key Performance Area - represents a strategic focus area
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_kpas',
        help_text="Senior Manager responsible for this KPA"
    )
    strategic_objective = models.TextField(
        help_text="High-level strategic objective this KPA supports"
    )
    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name='kpas'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order for KPAs"
    )
    is_active = models.BooleanField(default=True)
    org_units = models.ManyToManyField(OrgUnit, blank=True, related_name='kpas')

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "KPA"
        verbose_name_plural = "KPAs"
        unique_together = ['title', 'financial_year']

    def __str__(self):
        return f"{self.title} ({self.financial_year.year_code})"


class Staff(BaseModel):
    """Staff members within organizational units"""

    EMPLOYMENT_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent'),
        ('CONTRACT', 'Contract'),
        ('TEMPORARY', 'Temporary'),
        ('INTERN', 'Intern'),
        ('CONSULTANT', 'Consultant'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]

    QUALIFICATION_LEVEL_CHOICES = [
        ('MATRIC', 'Matric/Grade 12'),
        ('CERTIFICATE', 'Certificate'),
        ('DIPLOMA', 'Diploma'),
        ('DEGREE', 'Bachelor\'s Degree'),
        ('HONOURS', 'Honours Degree'),
        ('MASTERS', 'Master\'s Degree'),
        ('DOCTORATE', 'Doctorate'),
        ('OTHER', 'Other'),
    ]

    SALARY_LEVEL_CHOICES = [
        ('LEVEL_1', 'Level 1 - General Assistant'),
        ('LEVEL_2', 'Level 2 - General Assistant'),
        ('LEVEL_3', 'Level 3 - General Assistant'),
        ('LEVEL_4', 'Level 4 - Administrative Officer'),
        ('LEVEL_5', 'Level 5 - Senior Administrative Officer'),
        ('LEVEL_6', 'Level 6 - Senior Administrative Officer'),
        ('LEVEL_7', 'Level 7 - Senior Administrative Officer'),
        ('LEVEL_8', 'Level 8 - Assistant Director'),
        ('LEVEL_9', 'Level 9 - Assistant Director'),
        ('LEVEL_10', 'Level 10 - Assistant Director'),
        ('LEVEL_11', 'Level 11 - Deputy Director'),
        ('LEVEL_12', 'Level 12 - Deputy Director'),
        ('LEVEL_13', 'Level 13 - Director'),
        ('LEVEL_14', 'Level 14 - Chief Director'),
        ('LEVEL_15', 'Level 15 - Deputy Director-General'),
        ('LEVEL_16', 'Level 16 - Director-General'),
    ]

    # Personal Information
    persal_number = models.CharField(max_length=50, unique=True, help_text="Unique PERSAL number")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, help_text="Office phone number")
    cell_number = models.CharField(max_length=20, blank=True, help_text="Mobile/cell phone number")
    extension = models.CharField(max_length=10, blank=True, help_text="Office extension number")
    id_number = models.CharField(max_length=20, blank=True, help_text="National ID number")

    # Demographics
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    # Employment Details
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, related_name='staff_members')
    job_title = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='PERMANENT')
    salary_level = models.CharField(max_length=20, choices=SALARY_LEVEL_CHOICES, blank=True, help_text="Public service salary level")

    # Dates
    start_date = models.DateField(help_text="Employment start date")
    end_date = models.DateField(null=True, blank=True, help_text="Contract end date (if applicable)")

    # Qualifications and Skills
    highest_qualification = models.CharField(max_length=20, choices=QUALIFICATION_LEVEL_CHOICES, blank=True)
    qualification_details = models.TextField(blank=True, help_text="Detailed qualification information")
    skills = models.TextField(blank=True, help_text="Key skills and competencies")

    # Contact and Address
    physical_address = models.TextField(blank=True)
    postal_address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    # Performance and Development
    performance_rating = models.CharField(max_length=50, blank=True, help_text="Latest performance rating")
    development_needs = models.TextField(blank=True, help_text="Training and development needs")

    # Status
    is_active = models.BooleanField(default=True, help_text="Currently employed")
    is_manager = models.BooleanField(default=False, help_text="Has management responsibilities")

    class Meta:
        ordering = ['org_unit', 'last_name', 'first_name']
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.persal_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        """Validate the staff member data"""
        from django.core.exceptions import ValidationError
        from datetime import date

        # Validate dates
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date.")

        if self.start_date and self.start_date > date.today():
            raise ValidationError("Start date cannot be in the future.")

        if self.date_of_birth and self.start_date:
            age_at_start = (self.start_date - self.date_of_birth).days / 365.25
            if age_at_start < 16:
                raise ValidationError("Employee must be at least 16 years old at start date.")

    @property
    def is_contract_ending_soon(self):
        """Check if contract ends within 3 months"""
        if not self.end_date:
            return False
        from datetime import date, timedelta
        return self.end_date <= date.today() + timedelta(days=90)

    @property
    def years_of_service(self):
        """Calculate years of service"""
        if not self.start_date:
            return 0
        from datetime import date
        end_date = self.end_date if self.end_date and not self.is_active else date.today()
        delta = end_date - self.start_date
        return round(delta.days / 365.25, 1)


class OperationalPlanItem(BaseModel):
    """
    Represents a line item in the operational plan with all GCRA terminology
    """
    # Core identification
    kpa = models.ForeignKey(
        KPA,
        on_delete=models.CASCADE,
        related_name='plan_items'
    )

    # Operational Plan fields matching GCRA structure
    output = models.TextField(
        help_text="What is delivered - goods/services produced"
    )
    activities = models.JSONField(
        default=list,
        help_text="List of actions taken to deliver the output"
    )
    target_description = models.TextField(
        help_text="Desired measurable results"
    )
    indicator = models.CharField(
        max_length=500,
        help_text="How progress/success is measured"
    )
    inputs = models.JSONField(
        default=list,
        help_text="Resources required (human, financial, material)"
    )

    # Financial fields
    input_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost of inputs required"
    )
    output_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost to deliver the output"
    )

    # Timeframe and scheduling
    timeframe = models.CharField(
        max_length=200,
        help_text="When the output should be delivered"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Budget classification
    budget_programme = models.CharField(
        max_length=200,
        help_text="Budget programme classification"
    )
    budget_objective = models.CharField(
        max_length=200,
        help_text="Budget objective classification"
    )
    budget_responsibility = models.CharField(
        max_length=200,
        help_text="Budget responsibility center"
    )

    # Responsibility and organization
    responsible_officer = models.CharField(
        max_length=200,
        help_text="Name of the officer responsible for delivery"
    )
    unit_subdirectorate = models.CharField(
        max_length=200,
        blank=True,
        help_text="Unit or Sub-Directorate responsible"
    )
    office = models.CharField(
        max_length=200,
        blank=True,
        help_text="Office location or designation"
    )

    # Status and tracking
    is_active = models.BooleanField(default=True)
    priority = models.CharField(
        max_length=20,
        choices=[
            ('HIGH', 'High'),
            ('MEDIUM', 'Medium'),
            ('LOW', 'Low'),
        ],
        default='MEDIUM'
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or comments"
    )

    class Meta:
        ordering = ['kpa__order', 'id']
        verbose_name = "Operational Plan Item"
        verbose_name_plural = "Operational Plan Items"

    def __str__(self):
        return f"{self.output[:100]}... ({self.kpa.title})"

    @property
    def total_budget(self):
        """Calculate total budget (input + output costs)"""
        return self.input_cost + self.output_cost
