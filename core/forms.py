from django import forms
from django.contrib.auth.models import User
from .models import OperationalPlanItem, KPA, FinancialYear, OrgUnit


class GroupedManagerSelect(forms.Select):
    """Custom select widget that groups managers by organizational unit"""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        # Add custom styling for separators
        if value == '' and label.startswith('─'):
            option['attrs']['disabled'] = True
            option['attrs']['style'] = 'background-color: #f8f9fa; font-weight: bold; text-align: center;'

        return option


class OperationalPlanItemForm(forms.ModelForm):
    class Meta:
        model = OperationalPlanItem
        fields = [
            'kpa',
            'output',
            'target_description',
            'indicator',
            'timeframe',
            'start_date', 'end_date',
            'budget_programme',
            'budget_objective',
            'budget_responsibility',
            'responsible_officer',
            'unit_subdirectorate',
            'input_cost',
            'output_cost',
            'notes',
        ]
        widgets = {
            'output': forms.Textarea(attrs={'rows': 3}),
            'target_description': forms.Textarea(attrs={'rows': 2}),
            'indicator': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        financial_year = kwargs.pop('financial_year', None)
        super().__init__(*args, **kwargs)
        if financial_year is not None:
            self.fields['kpa'].queryset = KPA.objects.filter(financial_year=financial_year, is_active=True).order_by('order', 'title')
        # Set Bootstrap classes
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = widget.attrs.get('class', '')
                widget.attrs['class'] = (css + ' form-select js-choices').strip()
            elif isinstance(widget, forms.DateInput):
                css = widget.attrs.get('class', '')
                widget.attrs['class'] = (css + ' form-control js-date').strip()
            else:
                css = widget.attrs.get('class', '')
                widget.attrs['class'] = (css + ' form-control').strip()
        self.fields['input_cost'].widget.attrs.update({'placeholder': '0.00', 'data-currency': 'zar'})
        self.fields['output_cost'].widget.attrs.update({'placeholder': '0.00', 'data-currency': 'zar'})


class KPAForm(forms.ModelForm):
    class Meta:
        model = KPA
        fields = [
            'title', 'description', 'strategic_objective',
            'financial_year', 'owner', 'order', 'is_active', 'org_units'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'strategic_objective': forms.Textarea(attrs={'rows': 3}),
            'owner': GroupedManagerSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter owner field to show only managers (staff members with is_manager=True)
        from django.contrib.auth.models import User
        from accounts.models import UserProfile

        # Get users who are linked to staff members marked as managers
        manager_users = User.objects.filter(
            profile__staff_member__is_manager=True,
            profile__staff_member__is_active=True,
            is_active=True
        ).select_related('profile__staff_member').order_by(
            'profile__staff_member__org_unit__name',
            'first_name',
            'last_name'
        )

        self.fields['owner'].queryset = manager_users
        self.fields['owner'].empty_label = "Select a manager..."

        # Customize the display of manager options to show organizational context
        if manager_users.exists():
            choices = [('', 'Select a manager...')]
            current_unit = None

            for user in manager_users:
                staff = user.profile.staff_member
                unit_name = staff.org_unit.name

                # Add unit separator if this is a new unit
                if current_unit != unit_name:
                    if current_unit is not None:
                        choices.append(('', '─' * 50))  # Separator
                    current_unit = unit_name

                # Format: "Full Name (Job Title) - Unit Name"
                display_name = f"{user.get_full_name()} ({staff.job_title}) - {unit_name}"
                choices.append((user.id, display_name))

            self.fields['owner'].widget.choices = choices

        # Widget classes
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                css = w.attrs.get('class', '')
                w.attrs['class'] = (css + ' form-select js-choices').strip()
            elif isinstance(w, forms.Textarea):
                css = w.attrs.get('class', '')
                w.attrs['class'] = (css + ' form-control').strip()
            else:
                css = w.attrs.get('class', '')
                w.attrs['class'] = (css + ' form-control').strip()
        # Org units queryset and grouped choices by type
        qs = OrgUnit.objects.filter(is_active=True).order_by('unit_type', 'name')
        self.fields['org_units'].queryset = qs
        type_labels = dict(OrgUnit.UNIT_TYPE_CHOICES)
        grouped = {}
        for u in qs:
            grouped.setdefault(u.unit_type, []).append((u.id, u.name))
        self.fields['org_units'].choices = [
            (type_labels[t], opts) for t, opts in grouped.items()
        ]
        self.fields['org_units'].help_text = "Assign one or more organizational units (Chief Directorates, Directorates, Sub-Directorates)"

