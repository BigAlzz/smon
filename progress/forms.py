from django import forms
from django.core.exceptions import ValidationError
from .models import ProgressUpdate, Target, EvidenceFile
import os


class ProgressUpdateForm(forms.ModelForm):
    # Treat evidence URLs as free text textarea; we'll parse to list in clean
    evidence_urls = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))

    class Meta:
        model = ProgressUpdate
        fields = [
            'target', 'period_type', 'period_start', 'period_end', 'period_name',
            'actual_value', 'narrative', 'evidence_urls',
            'risk_rating', 'issues', 'corrective_actions',
            'forecast_value', 'forecast_confidence',
            'is_submitted',
        ]
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'period_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'period_name': forms.TextInput(attrs={'class': 'form-control'}),
            'actual_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'narrative': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'issues': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'corrective_actions': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'forecast_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'forecast_confidence': forms.Select(attrs={'class': 'form-select'}),
            'period_type': forms.Select(attrs={'class': 'form-select'}),
            'risk_rating': forms.Select(attrs={'class': 'form-select'}),
            'target': forms.Select(attrs={'class': 'form-select'}),
            'is_submitted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        plan_item = kwargs.pop('plan_item', None)
        previous_update = kwargs.pop('previous_update', None)
        super().__init__(*args, **kwargs)

        if plan_item is not None:
            self.fields['target'].queryset = Target.objects.filter(plan_item=plan_item, is_active=True)

        self.fields['evidence_urls'].required = False
        self.fields['forecast_value'].required = False

        # Pre-populate with previous update data if available and this is a new update
        if previous_update and not self.instance.pk:
            # Carry forward narrative, issues, and corrective actions for context
            if previous_update.narrative:
                self.fields['narrative'].widget.attrs['placeholder'] = f"Previous: {previous_update.narrative[:100]}..."
            if previous_update.issues:
                self.fields['issues'].widget.attrs['placeholder'] = f"Previous: {previous_update.issues[:100]}..."
            if previous_update.corrective_actions:
                self.fields['corrective_actions'].widget.attrs['placeholder'] = f"Previous: {previous_update.corrective_actions[:100]}..."

            # Set initial values for continuation
            if not self.initial.get('risk_rating'):
                self.initial['risk_rating'] = previous_update.risk_rating
            if not self.initial.get('forecast_value') and previous_update.forecast_value:
                self.initial['forecast_value'] = previous_update.forecast_value
            if not self.initial.get('forecast_confidence') and previous_update.forecast_confidence:
                self.initial['forecast_confidence'] = previous_update.forecast_confidence

    def clean_evidence_urls(self):
        data = self.cleaned_data.get('evidence_urls')
        if isinstance(data, list):
            return [x for x in data if str(x).strip()]
        text = data or ''
        lines = [l.strip() for l in str(text).splitlines() if l.strip()]
        return lines

    def clean(self):
        cleaned = super().clean()
        # Basic required fields
        for f in ['period_type', 'period_start', 'period_end', 'period_name', 'actual_value', 'narrative']:
            if not cleaned.get(f):
                self.add_error(f, 'This field is required.')
        # Evidence requirement rule
        try:
            target = cleaned.get('target') or getattr(self.instance, 'target', None)
            if target and cleaned.get('period_end') and cleaned.get('actual_value') is not None:
                from .models import ProgressUpdate as PU
                tmp = PU(
                    target=target,
                    period_start=cleaned.get('period_start') or cleaned.get('period_end'),
                    period_end=cleaned.get('period_end'),
                    period_type=cleaned.get('period_type') or 'MONTHLY',
                    period_name=cleaned.get('period_name') or '',
                    actual_value=cleaned.get('actual_value'),
                    narrative=cleaned.get('narrative') or '',
                )
                if tmp.is_evidence_required() and not cleaned.get('evidence_urls'):
                    self.add_error('evidence_urls', 'Evidence is required based on sustained Amber/Red status.')
        except Exception:
            pass
        return cleaned


class TargetForm(forms.ModelForm):
    class Meta:
        model = Target
        fields = [
            'name', 'value', 'unit', 'baseline',
            'due_date', 'periodicity', 'green_threshold', 'amber_threshold',
            'positive_tolerance', 'negative_tolerance', 'is_cumulative',
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            css = w.attrs.get('class', '')
            if isinstance(w, forms.DateInput):
                w.attrs['class'] = (css + ' form-control js-date').strip()
            elif isinstance(w, (forms.Select,)):
                w.attrs['class'] = (css + ' form-select js-choices').strip()
            else:
                w.attrs['class'] = (css + ' form-control').strip()


class EvidenceFileForm(forms.ModelForm):
    """
    Form for uploading evidence files
    """

    class Meta:
        model = EvidenceFile
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.xlsx,.xls,.docx,.doc,.png,.jpg,.jpeg,.gif,.csv,.txt',
                'multiple': False
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional description of this evidence file',
                'maxlength': 500
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['file'].help_text = (
            "Upload evidence files (PDF, Excel, Word, Images). "
            "Maximum file size: 10MB. "
            "Supported formats: PDF, Excel (.xlsx, .xls), Word (.docx, .doc), "
            "Images (.png, .jpg, .jpeg, .gif), CSV, Text files."
        )

        self.fields['description'].help_text = (
            "Provide a brief description of what this evidence demonstrates "
            "(e.g., 'Monthly sales report', 'Training completion certificates', etc.)"
        )

    def clean_file(self):
        """Validate uploaded file"""
        file = self.cleaned_data.get('file')

        if not file:
            return file

        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if file.size > max_size:
            raise ValidationError(
                f"File size ({round(file.size / (1024 * 1024), 2)}MB) exceeds "
                f"maximum allowed size of {max_size // (1024 * 1024)}MB."
            )

        # Check file extension
        allowed_extensions = [
            '.pdf', '.xlsx', '.xls', '.docx', '.doc',
            '.png', '.jpg', '.jpeg', '.gif', '.csv', '.txt'
        ]

        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(
                f"File type '{file_extension}' is not allowed. "
                f"Allowed types: {', '.join(allowed_extensions)}"
            )

        return file

    def save(self, commit=True):
        """Save the evidence file with additional metadata"""
        evidence_file = super().save(commit=False)

        if self.user:
            evidence_file.uploaded_by = self.user

        if evidence_file.file:
            evidence_file.original_filename = evidence_file.file.name
            evidence_file.file_size = evidence_file.file.size
            evidence_file.file_type = getattr(evidence_file.file, 'content_type', 'application/octet-stream')

        if commit:
            evidence_file.save()

        return evidence_file


class EvidenceUrlForm(forms.Form):
    """
    Form for adding evidence URLs
    """

    url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/evidence-document'
        }),
        help_text="URL to external evidence (e.g., shared drive, cloud storage, website)"
    )

    description = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Description of the evidence at this URL',
            'maxlength': 500
        }),
        help_text="Brief description of what can be found at this URL"
    )

