from rest_framework import serializers
from .models import Target, ProgressUpdate


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = [
            'id', 'plan_item', 'name', 'value', 'unit', 'baseline', 'due_date', 'periodicity',
            'green_threshold', 'amber_threshold', 'positive_tolerance', 'negative_tolerance',
            'is_cumulative', 'is_active'
        ]


class ProgressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressUpdate
        fields = [
            'id', 'target', 'period_type', 'period_start', 'period_end', 'period_name', 'actual_value',
            'narrative', 'evidence_urls', 'risk_rating', 'issues', 'corrective_actions',
            'forecast_value', 'forecast_confidence', 'is_submitted', 'is_approved',
        ]

