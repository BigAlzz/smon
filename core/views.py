"""
Core views including the Executive Dashboard
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import date
from decimal import Decimal
from django.db import models

from core.models import FinancialYear, KPA, OperationalPlanItem
from core.forms import KPAForm, OperationalPlanItemForm
from progress.models import Target, ProgressUpdate

# ---- Helpers for YTD, forecast, and spend calculations ----
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from progress.models import CostLine


def fy_bounds(fin_year: FinancialYear):
    return fin_year.start_date, fin_year.end_date


def months_elapsed(fin_year: FinancialYear, as_of: date) -> int:
    start, end = fy_bounds(fin_year)
    if as_of < start:
        return 0
    if as_of > end:
        as_of = end
    rd = relativedelta(as_of, start)
    # months elapsed inclusive of start month
    return rd.years * 12 + rd.months + 1


def quarters_elapsed(fin_year: FinancialYear, as_of: date) -> int:
    m = months_elapsed(fin_year, as_of)
    return min(4, (m + 2) // 3)  # ceil division by 3 up to 4


def latest_update_in_fy(target: Target, fin_year: FinancialYear, as_of: date):
    start, end = fy_bounds(fin_year)
    end = min(end, as_of)
    return (
        target.progress_updates.filter(period_end__gte=start, period_end__lte=end, is_active=True)
        .order_by('-period_end')
        .first()
    )


def sum_actuals_ytd(target: Target, fin_year: FinancialYear, as_of: date) -> Decimal:
    start, end = fy_bounds(fin_year)
    end = min(end, as_of)
    agg = (
        target.progress_updates.filter(period_end__gte=start, period_end__lte=end, is_active=True)
        .values_list('actual_value', flat=True)
    )
    total = Decimal('0.00')
    for v in agg:
        total += Decimal(v)
    return total


def ytd_target_value(target: Target, fin_year: FinancialYear, as_of: date) -> Decimal:
    # Compute YTD target based on periodicity
    total = target.value
    per = target.periodicity
    if per == 'ANNUAL':
        start, end = fy_bounds(fin_year)
        end_cut = min(end, as_of)
        elapsed_days = (end_cut - start).days + 1
        total_days = (end - start).days + 1
        return (total * Decimal(elapsed_days)) / Decimal(total_days) if total_days else Decimal('0.00')
    elif per == 'MONTHLY':
        m = months_elapsed(fin_year, as_of)
        return (total / Decimal('12')) * Decimal(m)
    elif per == 'QUARTERLY':
        q = quarters_elapsed(fin_year, as_of)
        return (total / Decimal('4')) * Decimal(q)
    else:
        return total


def compute_percent(ytd_actual: Decimal, ytd_target: Decimal) -> Decimal:
    if not ytd_target or ytd_target == 0:
        return Decimal('0.00')
    return (Decimal(ytd_actual) / Decimal(ytd_target)) * Decimal('100')


def compute_rag_from_percent(percent: Decimal, target: Target | None = None) -> str:
    green = Decimal('95.0')
    amber = Decimal('80.0')
    if target:
        green = target.green_threshold
        amber = target.amber_threshold
    if percent >= green:
        return 'GREEN'
    if percent >= amber:
        return 'AMBER'
    return 'RED'


def compute_forecast_value(target: Target, ytd_actual: Decimal, fin_year: FinancialYear, as_of: date) -> Decimal:
    # Use latest forecast if provided
    latest = latest_update_in_fy(target, fin_year, as_of)
    if latest and latest.forecast_value is not None:
        return Decimal(latest.forecast_value)
    # Otherwise linear projection by elapsed periods
    if target.periodicity == 'MONTHLY':
        m = months_elapsed(fin_year, as_of)
        if m <= 0:
            return Decimal('0.00')
        return (Decimal(ytd_actual) / Decimal(m)) * Decimal('12')
    if target.periodicity == 'QUARTERLY':
        q = quarters_elapsed(fin_year, as_of)
        if q <= 0:
            return Decimal('0.00')
        return (Decimal(ytd_actual) / Decimal(q)) * Decimal('4')
    # Annual: scale by days elapsed
    start, end = fy_bounds(fin_year)
    elapsed_days = (min(as_of, end) - start).days + 1
    total_days = (end - start).days + 1
    if elapsed_days <= 0:
        return Decimal('0.00')
    return (Decimal(ytd_actual) / Decimal(elapsed_days)) * Decimal(total_days)


def compute_item_spend(plan_item: OperationalPlanItem, fin_year: FinancialYear, as_of: date) -> tuple[Decimal, Decimal, Decimal]:
    planned = (plan_item.input_cost or Decimal('0.00')) + (plan_item.output_cost or Decimal('0.00'))
    start, end = fy_bounds(fin_year)
    end_cut = min(end, as_of)
    qs = plan_item.cost_lines.filter(cost_period_start__gte=start, cost_period_end__lte=end_cut, is_active=True)
    actual = Decimal('0.00')
    for cl in qs:
        actual += cl.actual_spend or Decimal('0.00')
    spend_pct = Decimal('0.00') if planned == 0 else (actual / planned) * Decimal('100')
    return planned, actual, spend_pct


@login_required
def dashboard_view(request):
    # Filters
    years = FinancialYear.objects.all().order_by('-start_date')
    selected_year_id = request.GET.get('year') or (years.first().id if years.exists() else None)
    selected_unit = request.GET.get('unit') or ''
    selected_period = request.GET.get('period') or 'YTD'

    # Dynamic period options based on financial year
    periods = [{'value': 'YTD', 'label': 'Year to Date'}]

    # Add monthly periods based on selected financial year
    if selected_year_id:
        try:
            selected_fy = FinancialYear.objects.get(id=selected_year_id)
            start_date = selected_fy.start_date
            end_date = selected_fy.end_date

            current_date = start_date
            month_num = 1

            while current_date <= end_date:
                periods.append({
                    'value': f'M{month_num:02d}',
                    'label': current_date.strftime('%B %Y')
                })

                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

                month_num += 1

                # Safety check to prevent infinite loop
                if month_num > 12:
                    break

        except FinancialYear.DoesNotExist:
            pass

    # Build KPA cards with real calculations
    as_of = timezone.now().date()
    kpas = KPA.objects.select_related('financial_year', 'owner').filter(
        financial_year_id=selected_year_id
    ) if selected_year_id else KPA.objects.none()

    # Optionally filter by unit
    plan_items_qs = OperationalPlanItem.objects.filter(kpa__in=kpas, is_active=True)
    if selected_unit:
        plan_items_qs = plan_items_qs.filter(unit_subdirectorate=selected_unit)

    kpa_items_map = defaultdict(list)
    for pi in plan_items_qs.select_related('kpa'):
        kpa_items_map[pi.kpa_id].append(pi)

    kpa_cards = []
    on_track = at_risk = off_track = 0
    total_planned_budget = Decimal('0.00')
    total_actual_spend = Decimal('0.00')

    for k in kpas:
        items = kpa_items_map.get(k.id, [])
        agg_ytd_target = Decimal('0.00')
        agg_ytd_actual = Decimal('0.00')
        kpa_planned = Decimal('0.00')
        kpa_spent = Decimal('0.00')

        for item in items:
            # Sum planned vs spend for item
            planned, actual_spend, _spend_pct = compute_item_spend(item, k.financial_year, as_of)
            kpa_planned += planned
            kpa_spent += actual_spend

            # For each active target on this plan item
            targets = Target.objects.filter(plan_item=item, is_active=True)
            for t in targets:
                ytd_tgt = ytd_target_value(t, k.financial_year, as_of)
                ytd_act = sum_actuals_ytd(t, k.financial_year, as_of)
                agg_ytd_target += ytd_tgt
                agg_ytd_actual += ytd_act

        total_planned_budget += kpa_planned
        total_actual_spend += kpa_spent

        percent = compute_percent(agg_ytd_actual, agg_ytd_target)
        rag = compute_rag_from_percent(percent)
        color = '#28a745' if rag == 'GREEN' else '#ffc107' if rag == 'AMBER' else '#dc3545'

        if rag == 'GREEN':
            on_track += 1
        elif rag == 'AMBER':
            at_risk += 1
        elif rag == 'RED':
            off_track += 1

        kpa_cards.append({
            'title': k.title,
            'id': k.id,
            'owner': k.owner.get_full_name() or k.owner.username,
            'rag': rag,
            'color': color,
            'ytd_target': agg_ytd_target,
            'ytd_actual': agg_ytd_actual,
            'percent': round(percent),
            'budget_burn_pct': (Decimal('0.00') if kpa_planned == 0 else (kpa_spent / kpa_planned) * Decimal('100')),
        })

    overall_burn = Decimal('0.00') if total_planned_budget == 0 else (total_actual_spend / total_planned_budget) * Decimal('100')

    # Compute CEO-friendly overview metrics
    total_kpas = len(kpa_cards)
    if total_kpas > 0:
        avg_percent = sum(card['percent'] for card in kpa_cards) / total_kpas
    else:
        avg_percent = 0

    overall_score = int(round(avg_percent))
    overall_remaining = max(0, 100 - overall_score)

    # Only include calculated metrics if we have data
    summary = {
        'on_track': on_track,
        'at_risk': at_risk,
        'off_track': off_track,
        'total_kpas': total_kpas,
    }

    # Add calculated metrics only if we have KPAs
    if total_kpas > 0:
        summary.update({
            'budget_burn': f"{overall_burn.quantize(Decimal('1.'))}%" if overall_burn >= 1 else f"{overall_burn.quantize(Decimal('1.00'))}%",
            'overall_score': overall_score,
            'overall_remaining': overall_remaining,
            'target_achievement': int(round(avg_percent)) if avg_percent > 0 else None,
            'timeline_adherence': None,  # This would need to be calculated based on actual timeline data
        })
    else:
        summary.update({
            'budget_burn': None,
            'overall_score': None,
            'overall_remaining': None,
            'target_achievement': None,
            'timeline_adherence': None,
        })

    # Units list
    units = sorted(set(pi.unit_subdirectorate for pi in plan_items_qs if pi.unit_subdirectorate))

    context = {
        'years': years,
        'selected_year_id': selected_year_id,
        'units': units,
        'selected_unit': selected_unit,
        'periods': periods,
        'selected_period': selected_period,
        'kpa_cards': kpa_cards,
        'summary': summary,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def kpa_drilldown_view(request, kpa_id):
    """KPA Drilldown page showing items and progress for a given KPA"""
    kpa = get_object_or_404(KPA.objects.select_related('financial_year', 'owner'), id=kpa_id)

    # TODO: apply permission checks by role/unit if needed
    # Build table rows from plan items, targets and latest progress updates (real calculations)
    as_of = timezone.now().date()
    plan_items = OperationalPlanItem.objects.filter(kpa=kpa, is_active=True).order_by('id')

    rows = []
    for item in plan_items:
        # Sum across all active targets for this item
        ytd_target = Decimal('0.00')
        ytd_actual = Decimal('0.00')
        forecast = Decimal('0.00')
        rag = 'GREY'
        rag_counts = {'GREEN': 0, 'AMBER': 0, 'RED': 0}

        targets = Target.objects.filter(plan_item=item, is_active=True)
        for t in targets:
            t_ytd_tgt = ytd_target_value(t, kpa.financial_year, as_of)
            t_ytd_act = sum_actuals_ytd(t, kpa.financial_year, as_of)
            t_percent = compute_percent(t_ytd_act, t_ytd_tgt)
            t_rag = compute_rag_from_percent(t_percent, t)
            t_forecast = compute_forecast_value(t, t_ytd_act, kpa.financial_year, as_of)

            ytd_target += t_ytd_tgt
            ytd_actual += t_ytd_act
            forecast += t_forecast
            rag_counts[t_rag] += 1

        # Decide item RAG (worst-case among RED>AMBER>GREEN)
        if rag_counts['RED']:
            rag = 'RED'
        elif rag_counts['AMBER']:
            rag = 'AMBER'
        elif rag_counts['GREEN']:
            rag = 'GREEN'
        else:
            rag = 'GREY'

        variance = ytd_actual - ytd_target

        # Spend alignment
        planned_budget, actual_spend, spend_pct = compute_item_spend(item, kpa.financial_year, as_of)
        progress_pct = compute_percent(ytd_actual, ytd_target)
        spend_alignment_flag = False
        # Flag when spend significantly exceeds progress (e.g., >20% gap)
        try:
            spend_alignment_flag = (spend_pct - progress_pct) > Decimal('20')
        except Exception:
            spend_alignment_flag = False

        # Get the first target ID if it exists
        first_target_id = Target.objects.filter(plan_item=item, is_active=True).values_list('id', flat=True).first()

        rows.append({
            'output': item.output,
            'indicator': item.indicator,
            'ytd_target': ytd_target,
            'ytd_actual': ytd_actual,
            'variance': variance,
            'rag': rag,
            'owner': item.responsible_officer,
            'item_id': str(item.id),
            'target_id': str(first_target_id) if first_target_id else None,
            'forecast': forecast,
            'planned_budget': planned_budget,
            'actual_spend': actual_spend,
            'spend_pct': spend_pct,
            'progress_pct': progress_pct,
            'spend_alignment_flag': spend_alignment_flag,
        })

    context = {
        'kpa': kpa,
        'rows': rows,
    }
    return render(request, 'kpa/drilldown.html', context)

@login_required
def plan_grid_view(request):
    years = FinancialYear.objects.all().order_by('-start_date')
    selected_year_id = request.GET.get('year') or (years.first().id if years.exists() else None)
    selected_kpa_id = request.GET.get('kpa') or ''
    selected_unit = request.GET.get('unit') or ''

    kpas = KPA.objects.filter(financial_year_id=selected_year_id) if selected_year_id else KPA.objects.none()

    qs = OperationalPlanItem.objects.select_related('kpa').filter(kpa__in=kpas, is_active=True)
    if selected_kpa_id:
        qs = qs.filter(kpa_id=selected_kpa_id)
    if selected_unit:
        qs = qs.filter(unit_subdirectorate=selected_unit)

    # Units list from current query scope
    units = sorted(set(qs.values_list('unit_subdirectorate', flat=True)))

    # Handle sorting
    sort_field = request.GET.get('sort', 'kpa__order')
    sort_order = request.GET.get('order', 'asc')

    # Define allowed sort fields to prevent SQL injection
    allowed_sort_fields = {
        'output': 'output',
        'indicator': 'indicator',
        'target_description': 'target_description',
        'timeframe': 'timeframe',
        'responsible_officer': 'responsible_officer',
        'unit_subdirectorate': 'unit_subdirectorate',
        'input_cost': 'input_cost',
        'output_cost': 'output_cost',
        'kpa__order': 'kpa__order',
    }

    if sort_field in allowed_sort_fields:
        order_by = allowed_sort_fields[sort_field]
        if sort_order == 'desc':
            order_by = f'-{order_by}'
    else:
        order_by = 'kpa__order'

    # Add secondary sort to ensure consistent ordering
    if sort_field != 'kpa__order':
        order_by = [order_by, 'kpa__order', 'id']
    else:
        order_by = [order_by, 'id']

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(qs.order_by(*order_by), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'years': years,
        'selected_year_id': selected_year_id,
        'kpas': kpas,
        'selected_kpa_id': selected_kpa_id,
        'units': [u for u in units if u],
        'selected_unit': selected_unit,
        'page_obj': page_obj,
    }
    return render(request, 'plan/grid.html', context)


@login_required
def plan_item_update_field(request, item_id):
    """AJAX endpoint to update a single field on an OperationalPlanItem"""
    if request.method != 'POST':
        from django.http import JsonResponse
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    from django.http import JsonResponse
    from accounts.models import AuditLog, UserProfile

    item = get_object_or_404(OperationalPlanItem, id=item_id)

    # Permission check
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.can_edit_plan_item(item):
        return JsonResponse({'error': 'Not authorized'}, status=403)

    field = request.POST.get('field')
    value = request.POST.get('value', '').strip()

    allowed_fields = {
        'target_description': 'str',
        'responsible_officer': 'str',
        'unit_subdirectorate': 'str',
        'budget_programme': 'str',
        'input_cost': 'decimal',
        'output_cost': 'decimal',
    }

    if field not in allowed_fields:
        return JsonResponse({'error': 'Field not allowed'}, status=400)

    # Validate and convert
    old_value = getattr(item, field)
    try:
        if allowed_fields[field] == 'decimal':
            if value == '':
                value_dec = Decimal('0.00')
            else:
                value_dec = Decimal(value.replace(',', ''))
                if value_dec < 0:
                    return JsonResponse({'error': 'Value must be non-negative'}, status=400)
            setattr(item, field, value_dec)
            display_value = f"R {value_dec:,.2f}"
        else:
            if len(value) > 500:
                return JsonResponse({'error': 'Value too long'}, status=400)
            setattr(item, field, value)
            display_value = value
    except Exception:
        return JsonResponse({'error': 'Invalid value'}, status=400)

    # Save with audit metadata
    item.updated_by = request.user
    item.save()

    # Audit log
    try:
        AuditLog.objects.create(
            user=request.user,
            user_email=request.user.email,
            user_ip_address=request.META.get('REMOTE_ADDR'),
            action='UPDATE',
            model_name='OperationalPlanItem',
            object_id=str(item.id),
            object_repr=str(item),
            changes={'field': field, 'old': str(old_value), 'new': str(getattr(item, field))},
            session_key=getattr(request, 'session', None) and request.session.session_key,
        )
    except Exception:
        pass

    return JsonResponse({'ok': True, 'field': field, 'display': display_value})



@login_required
def plan_item_create_view(request):
    years = FinancialYear.objects.all().order_by('-start_date')
    current_year = years.first() if years.exists() else None

    if request.method == 'POST':
        form = OperationalPlanItemForm(request.POST, financial_year=current_year)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.updated_by = request.user
            item.save()
            # Audit log (best-effort)
            try:
                from accounts.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    user_email=request.user.email,
                    user_ip_address=request.META.get('REMOTE_ADDR'),
                    action='CREATE',
                    model_name='OperationalPlanItem',
                    object_id=str(item.id),
                    object_repr=str(item),
                    changes={'created_fields': {k: str(v) for k, v in form.cleaned_data.items()}},
                    session_key=getattr(request, 'session', None) and request.session.session_key,
                )
            except Exception:
                pass
            from django.shortcuts import redirect
            return redirect('plan_grid')
    else:
        form = OperationalPlanItemForm(financial_year=current_year)

    return render(request, 'plan/item_form.html', {'form': form})

def _check_kpa_permissions(user, action='create'):
    """Helper function to check KPA management permissions"""
    prof = getattr(user, 'profile', None)

    # For viewing KPAs, allow all authenticated users
    if action == 'view':
        return  # All authenticated users can view KPAs

    # For create/edit/delete operations, check roles
    allowed_roles = {'SENIOR_MANAGER', 'PROGRAMME_MANAGER', 'ME_STRATEGY', 'SYSTEM_ADMIN'}

    # Also allow managers (staff members marked as managers)
    is_staff_manager = False
    if prof and hasattr(prof, 'staff_member') and prof.staff_member:
        is_staff_manager = prof.staff_member.is_manager

    if not prof or (prof.primary_role not in allowed_roles and not is_staff_manager):
        raise PermissionDenied(f"You are not allowed to {action} KPAs.")

def _get_org_units_data():
    """Helper function to get org units data for forms"""
    from core.models import OrgUnit
    import json
    org_units_all = OrgUnit.objects.filter(is_active=True).select_related('parent').order_by('unit_type','name')
    org_units_data = [
        {
            'id': str(u.id),
            'name': u.name,
            'type': u.unit_type,
            'parent': str(u.parent_id) if u.parent_id else None,
        } for u in org_units_all
    ]
    return org_units_all, json.dumps(org_units_data)

def _log_kpa_action(user, action, kpa, changes=None, request=None):
    """Helper function to log KPA actions"""
    try:
        from accounts.models import AuditLog
        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            user_ip_address=request.META.get('REMOTE_ADDR') if request else None,
            action=action,
            model_name='KPA',
            object_id=str(kpa.id),
            object_repr=str(kpa),
            changes=changes or {},
            session_key=getattr(request, 'session', None) and request.session.session_key if request else None,
        )
    except Exception:
        pass

@login_required
def kpa_list_view(request):
    """List all KPAs with filtering and management options"""
    _check_kpa_permissions(request.user, 'view')

    # Filters
    years = FinancialYear.objects.all().order_by('-start_date')
    selected_year_id = request.GET.get('year') or (years.first().id if years.exists() else None)
    search_query = request.GET.get('search', '').strip()

    # Base queryset
    kpas = KPA.objects.select_related('financial_year', 'owner').prefetch_related('org_units')

    # Apply filters
    if selected_year_id:
        kpas = kpas.filter(financial_year_id=selected_year_id)

    if search_query:
        kpas = kpas.filter(
            models.Q(title__icontains=search_query) |
            models.Q(description__icontains=search_query) |
            models.Q(strategic_objective__icontains=search_query)
        )

    # Handle sorting
    sort_field = request.GET.get('sort', 'order')
    sort_order = request.GET.get('order', 'asc')

    # Define allowed sort fields to prevent SQL injection
    allowed_sort_fields = {
        'title': 'title',
        'financial_year': 'financial_year__year_code',
        'owner': 'owner__last_name',
        'order': 'order',
        'is_active': 'is_active',
    }

    if sort_field in allowed_sort_fields:
        order_by = allowed_sort_fields[sort_field]
        if sort_order == 'desc':
            order_by = f'-{order_by}'
    else:
        order_by = 'order'

    # Add secondary sort to ensure consistent ordering
    if sort_field != 'order':
        order_by = [order_by, 'order', 'title']
    else:
        order_by = [order_by, 'title']

    kpas = kpas.order_by(*order_by)

    # Statistics
    total_kpas = KPA.objects.count()
    active_kpas = KPA.objects.filter(is_active=True).count()
    current_year_kpas = KPA.objects.filter(financial_year_id=selected_year_id).count() if selected_year_id else 0

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(kpas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'years': years,
        'selected_year_id': selected_year_id,
        'search_query': search_query,
        'stats': {
            'total_kpas': total_kpas,
            'active_kpas': active_kpas,
            'current_year_kpas': current_year_kpas,
        }
    }
    return render(request, 'kpa/list.html', context)

@login_required
def kpa_create_view(request):
    """Create a new KPA"""
    _check_kpa_permissions(request.user, 'create')

    if request.method == 'POST':
        form = KPAForm(request.POST)
        if form.is_valid():
            kpa = form.save(commit=False)
            kpa.created_by = request.user
            kpa.updated_by = request.user
            kpa.save()
            form.save_m2m()

            _log_kpa_action(request.user, 'CREATE', kpa,
                          {'created_fields': {k: str(v) for k, v in form.cleaned_data.items()}}, request)

            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, f'KPA "{kpa.title}" created successfully.')
            return redirect('kpa_list')
    else:
        form = KPAForm()

    org_units_all, org_units_data = _get_org_units_data()

    return render(request, 'kpa/form.html', {
        'form': form,
        'org_units_all': org_units_all,
        'org_units_data': org_units_data,
        'action': 'Create',
    })

@login_required
def kpa_edit_view(request, kpa_id):
    """Edit an existing KPA"""
    _check_kpa_permissions(request.user, 'edit')

    kpa = get_object_or_404(KPA, id=kpa_id)

    if request.method == 'POST':
        form = KPAForm(request.POST, instance=kpa)
        if form.is_valid():
            # Track changes for audit log
            old_values = {field: getattr(kpa, field) for field in form.changed_data}

            kpa = form.save(commit=False)
            kpa.updated_by = request.user
            kpa.save()
            form.save_m2m()

            # Log changes
            new_values = {field: getattr(kpa, field) for field in form.changed_data}
            changes = {
                'changed_fields': form.changed_data,
                'old_values': {k: str(v) for k, v in old_values.items()},
                'new_values': {k: str(v) for k, v in new_values.items()},
            }
            _log_kpa_action(request.user, 'UPDATE', kpa, changes, request)

            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, f'KPA "{kpa.title}" updated successfully.')
            return redirect('kpa_list')
    else:
        form = KPAForm(instance=kpa)

    org_units_all, org_units_data = _get_org_units_data()

    return render(request, 'kpa/form.html', {
        'form': form,
        'org_units_all': org_units_all,
        'org_units_data': org_units_data,
        'action': 'Edit',
        'kpa': kpa,
    })

@login_required
def kpa_delete_view(request, kpa_id):
    """Delete a KPA"""
    _check_kpa_permissions(request.user, 'delete')

    kpa = get_object_or_404(KPA, id=kpa_id)

    # Check if KPA has operational plan items
    plan_items_count = OperationalPlanItem.objects.filter(kpa=kpa).count()

    if request.method == 'POST':
        if request.POST.get('confirm') == 'yes':
            kpa_title = kpa.title
            _log_kpa_action(request.user, 'DELETE', kpa,
                          {'deleted_kpa': str(kpa)}, request)

            kpa.delete()

            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, f'KPA "{kpa_title}" deleted successfully.')
            return redirect('kpa_list')

    context = {
        'kpa': kpa,
        'plan_items_count': plan_items_count,
    }
    return render(request, 'kpa/delete.html', context)


@login_required
def target_create_view(request, item_id):
    from progress.forms import TargetForm
    item = get_object_or_404(OperationalPlanItem, id=item_id)
    # Permissions: reuse plan item edit permission
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.can_edit_plan_item(item):
        raise PermissionDenied("Not allowed")

    if request.method == 'POST':
        form = TargetForm(request.POST)
        if form.is_valid():
            target = form.save(commit=False)
            target.plan_item = item
            target.created_by = request.user
            target.updated_by = request.user
            target.save()
            # Audit log best-effort
            try:
                from accounts.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    user_email=request.user.email,
                    user_ip_address=request.META.get('REMOTE_ADDR'),
                    action='CREATE',
                    model_name='Target',
                    object_id=str(target.id),
                    object_repr=str(target),
                    changes={'created_fields': {k: str(v) for k, v in form.cleaned_data.items()}},
                    session_key=getattr(request, 'session', None) and request.session.session_key,
                )
            except Exception:
                pass
            from django.shortcuts import redirect
            return redirect('kpa_drilldown', kpa_id=item.kpa_id)
    else:
        form = TargetForm()

    return render(request, 'target/form.html', {'form': form, 'back_url': request.META.get('HTTP_REFERER', '/')})


@login_required
def item_detail_view(request, item_id):
    item = get_object_or_404(OperationalPlanItem, id=item_id)
    targets = Target.objects.filter(plan_item=item, is_active=True).order_by('due_date')
    recent_updates = ProgressUpdate.objects.filter(target__in=targets, is_active=True).order_by('-period_end')[:20]
    return render(request, 'plan/item_detail.html', {
        'item': item,
        'targets': targets,
        'recent_updates': recent_updates,
    })


@login_required
def update_wizard_view(request, target_id):
    target = get_object_or_404(Target, id=target_id)
    # Permissions: can update if user can edit plan item
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.can_edit_plan_item(target.plan_item):
        raise PermissionDenied("Not allowed")

    if request.method == 'POST':
        from progress.forms import ProgressUpdateForm
        form = ProgressUpdateForm(request.POST, plan_item=target.plan_item)
        if form.is_valid():
            # Quarter lock check
            try:
                from core.utils_time import is_period_locked
                fin_year = target.plan_item.kpa.financial_year
                if is_period_locked(fin_year, form.cleaned_data['period_end']):
                    form.add_error(None, 'This quarter is locked. Edits are no longer allowed for the selected period.')
                    raise ValueError('Quarter locked')
            except Exception:
                pass

            if not form.errors:
                upd = form.save(commit=False)
                upd.target = target
                upd.created_by = request.user
                upd.updated_by = request.user
                upd.is_submitted = True
                upd.save()
                try:
                    from accounts.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        user_email=request.user.email,
                        user_ip_address=request.META.get('REMOTE_ADDR'),
                        action='CREATE',
                        model_name='ProgressUpdate',
                        object_id=str(upd.id),
                        object_repr=str(upd),
                        changes={'created_fields': {k: str(v) for k, v in form.cleaned_data.items()}},
                        session_key=getattr(request, 'session', None) and request.session.session_key,
                    )
                except Exception:
                    pass

                # Add success message
                from django.contrib import messages
                messages.success(
                    request,
                    f"✅ Progress update for '{target.name}' has been successfully submitted! "
                    f"Your update shows {upd.actual_value} {target.get_unit_display} "
                    f"({upd.percentage_complete:.1f}% complete) with {upd.rag_status} status."
                )

                from django.shortcuts import redirect
                return redirect('item_detail', item_id=target.plan_item_id)
    else:
        from progress.forms import ProgressUpdateForm
        form = ProgressUpdateForm(plan_item=target.plan_item)

    # Evidence enforcement flag
    evidence_required = False
    try:
        # A temporary instance to evaluate business rule
        from progress.models import ProgressUpdate as PU
        tmp = PU(target=target, period_start=timezone.now().date(), period_end=timezone.now().date(), period_type='MONTHLY', period_name='')
        evidence_required = tmp.is_evidence_required()
    except Exception:
        evidence_required = False

    return render(request, 'progress/update_wizard.html', {
        'target': target,
        'form': form,
        'back_url': request.META.get('HTTP_REFERER', '/'),
        'evidence_required': evidence_required,
    })


@login_required
@require_http_methods(["GET", "POST"])
def csrf_debug_view(request):
    """Debug view to check CSRF token status"""
    try:
        from django.middleware.csrf import get_token
        from django.http import JsonResponse

        csrf_token = get_token(request)

        debug_info = {
            'status': 'success',
            'csrf_token': csrf_token,
            'method': request.method,
            'cookies': {k: v for k, v in request.COOKIES.items()},
            'session_key': request.session.session_key,
            'user': str(request.user),
            'is_authenticated': request.user.is_authenticated,
            'timestamp': timezone.now().isoformat(),
        }

        # Add relevant headers (filter out sensitive ones)
        safe_headers = {}
        for k, v in request.META.items():
            if k.startswith('HTTP_') and k not in ['HTTP_AUTHORIZATION', 'HTTP_COOKIE']:
                safe_headers[k] = v
        debug_info['headers'] = safe_headers

        if request.method == 'POST':
            debug_info['post_data'] = {k: v for k, v in request.POST.items()}
            debug_info['csrf_from_post'] = request.POST.get('csrfmiddlewaretoken', 'NOT_FOUND')
            debug_info['csrf_header'] = request.META.get('HTTP_X_CSRFTOKEN', 'NOT_FOUND')

        return JsonResponse(debug_info, indent=2)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'method': request.method,
            'user': str(request.user),
            'timestamp': timezone.now().isoformat(),
        }, status=500)


@login_required
def csrf_test_view(request):
    """Test page for CSRF functionality"""
    return render(request, 'debug/csrf_test.html')
