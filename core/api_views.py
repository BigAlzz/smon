from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import FinancialYear, KPA, OperationalPlanItem
from .api_serializers import FinancialYearSerializer, KPASerializer, OperationalPlanItemSerializer
from progress.models import Target, ProgressUpdate
from progress.api_serializers import TargetSerializer, ProgressUpdateSerializer
from core.utils_time import is_period_locked


class IsAuthenticatedRBAC(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view)


class FinancialYearViewSet(viewsets.ModelViewSet):
    queryset = FinancialYear.objects.all()
    serializer_class = FinancialYearSerializer
    permission_classes = [IsAuthenticatedRBAC]


class KPAViewSet(viewsets.ModelViewSet):
    queryset = KPA.objects.all()
    serializer_class = KPASerializer
    permission_classes = [IsAuthenticatedRBAC]


class OperationalPlanItemViewSet(viewsets.ModelViewSet):
    queryset = OperationalPlanItem.objects.all()
    serializer_class = OperationalPlanItemSerializer
    permission_classes = [IsAuthenticatedRBAC]
    filterset_fields = ['kpa', 'unit_subdirectorate', 'is_active']
    search_fields = ['output', 'indicator', 'target_description']


class TargetViewSet(viewsets.ModelViewSet):
    queryset = Target.objects.all()
    serializer_class = TargetSerializer
    permission_classes = [IsAuthenticatedRBAC]
    filterset_fields = ['plan_item', 'periodicity', 'is_active']


class ProgressUpdateViewSet(viewsets.ModelViewSet):
    queryset = ProgressUpdate.objects.all()
    serializer_class = ProgressUpdateSerializer
    permission_classes = [IsAuthenticatedRBAC]
    filterset_fields = ['target', 'period_type', 'is_submitted', 'is_approved']
    search_fields = ['period_name', 'narrative']

    @action(detail=False, methods=['post'], url_path='draft')
    def save_draft(self, request):
        """Create or update a draft ProgressUpdate for autosave.
        Drafts are identified by (target, period_start, period_end), with is_submitted=False.
        """
        try:
            target_id = request.data.get('target') or request.data.get('target_id')
            target = get_object_or_404(Target, id=target_id)
        except Exception:
            return Response({'error': 'Target is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # RBAC: same as web view
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.can_edit_plan_item(target.plan_item):
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        # Quarter lock
        fin_year = target.plan_item.kpa.financial_year
        try:
            period_end = request.data.get('period_end')
            if period_end:
                from datetime import datetime
                period_end_dt = datetime.fromisoformat(period_end).date()
                if is_period_locked(fin_year, period_end_dt):
                    return Response({'error': 'Quarter is locked for this period.'}, status=status.HTTP_423_LOCKED)
        except Exception:
            pass

        # Upsert by composite
        # Normalize incoming data to a plain dict (avoid QueryDict quirks)
        raw = request.data
        try:
            from django.http import QueryDict
            if isinstance(raw, QueryDict):
                payload = {k: raw.get(k) for k in raw.keys()}
            else:
                payload = dict(raw)
        except Exception:
            payload = dict(raw)

        # evidence_urls handling: accept textarea text or array
        ev = payload.get('evidence_urls')
        if isinstance(ev, str):
            payload['evidence_urls'] = [l.strip() for l in ev.splitlines() if l.strip()]
        elif isinstance(ev, list):
            payload['evidence_urls'] = [str(l).strip() for l in ev if str(l).strip()]

        payload['is_submitted'] = False
        ser = ProgressUpdateSerializer(data=payload)
        if not ser.is_valid():
            return Response({'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Find existing draft
        existing = ProgressUpdate.objects.filter(
            target=target,
            period_start=ser.validated_data['period_start'],
            period_end=ser.validated_data['period_end'],
            is_submitted=False,
            is_active=True,
        ).first()

        if existing:
            for k, v in ser.validated_data.items():
                setattr(existing, k, v)
            existing.updated_by = request.user
            existing.save()
            out = ProgressUpdateSerializer(existing)
            return Response({'ok': True, 'id': existing.id, 'saved': timezone.now().isoformat(), 'data': out.data})
        else:
            obj = ser.save(created_by=request.user, updated_by=request.user)
            out = ProgressUpdateSerializer(obj)
            return Response({'ok': True, 'id': obj.id, 'saved': timezone.now().isoformat(), 'data': out.data})

