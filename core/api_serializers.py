from rest_framework import serializers
from .models import FinancialYear, KPA, OperationalPlanItem
from progress.models import Target, ProgressUpdate


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = ['id', 'year_code', 'start_date', 'end_date', 'is_active']


class KPASerializer(serializers.ModelSerializer):
    financial_year = FinancialYearSerializer(read_only=True)
    financial_year_id = serializers.PrimaryKeyRelatedField(
        source='financial_year', queryset=FinancialYear.objects.all(), write_only=True
    )

    class Meta:
        model = KPA
        fields = ['id', 'title', 'description', 'strategic_objective', 'owner', 'order', 'is_active',
                  'financial_year', 'financial_year_id']


class OperationalPlanItemSerializer(serializers.ModelSerializer):
    kpa = KPASerializer(read_only=True)
    kpa_id = serializers.PrimaryKeyRelatedField(source='kpa', queryset=KPA.objects.all(), write_only=True)

    class Meta:
        model = OperationalPlanItem
        fields = [
            'id', 'kpa', 'kpa_id', 'output', 'target_description', 'indicator', 'timeframe',
            'start_date', 'end_date', 'budget_programme', 'budget_objective', 'budget_responsibility',
            'responsible_officer', 'unit_subdirectorate', 'input_cost', 'output_cost', 'notes', 'is_active'
        ]

