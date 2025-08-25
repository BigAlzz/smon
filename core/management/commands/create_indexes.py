"""
Management command to create database indexes for performance optimization
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Create database indexes for performance optimization'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating database indexes...'))
        
        with connection.cursor() as cursor:
            # Core model indexes
            indexes = [
                # FinancialYear indexes
                "CREATE INDEX IF NOT EXISTS idx_financialyear_active ON core_financialyear(is_active) WHERE is_active = true;",
                "CREATE INDEX IF NOT EXISTS idx_financialyear_dates ON core_financialyear(start_date, end_date);",
                
                # KPA indexes
                "CREATE INDEX IF NOT EXISTS idx_kpa_financial_year ON core_kpa(financial_year_id);",
                "CREATE INDEX IF NOT EXISTS idx_kpa_owner ON core_kpa(owner_id);",
                "CREATE INDEX IF NOT EXISTS idx_kpa_active ON core_kpa(is_active) WHERE is_active = true;",
                "CREATE INDEX IF NOT EXISTS idx_kpa_order ON core_kpa(\"order\", title);",
                
                # OperationalPlanItem indexes
                "CREATE INDEX IF NOT EXISTS idx_planitem_kpa ON core_operationalplanitem(kpa_id);",
                "CREATE INDEX IF NOT EXISTS idx_planitem_active ON core_operationalplanitem(is_active) WHERE is_active = true;",
                "CREATE INDEX IF NOT EXISTS idx_planitem_priority ON core_operationalplanitem(priority);",
                "CREATE INDEX IF NOT EXISTS idx_planitem_budget_programme ON core_operationalplanitem(budget_programme);",
                "CREATE INDEX IF NOT EXISTS idx_planitem_responsible_officer ON core_operationalplanitem(responsible_officer);",
                "CREATE INDEX IF NOT EXISTS idx_planitem_dates ON core_operationalplanitem(start_date, end_date);",
                
                # Target indexes
                "CREATE INDEX IF NOT EXISTS idx_target_plan_item ON progress_target(plan_item_id);",
                "CREATE INDEX IF NOT EXISTS idx_target_due_date ON progress_target(due_date);",
                "CREATE INDEX IF NOT EXISTS idx_target_active ON progress_target(is_active) WHERE is_active = true;",
                "CREATE INDEX IF NOT EXISTS idx_target_periodicity ON progress_target(periodicity);",
                
                # ProgressUpdate indexes
                "CREATE INDEX IF NOT EXISTS idx_progress_target ON progress_progressupdate(target_id);",
                "CREATE INDEX IF NOT EXISTS idx_progress_period ON progress_progressupdate(period_start, period_end);",
                "CREATE INDEX IF NOT EXISTS idx_progress_submitted ON progress_progressupdate(is_submitted, submitted_at);",
                "CREATE INDEX IF NOT EXISTS idx_progress_approved ON progress_progressupdate(is_approved, approved_at);",
                "CREATE INDEX IF NOT EXISTS idx_progress_risk ON progress_progressupdate(risk_rating);",
                "CREATE INDEX IF NOT EXISTS idx_progress_active ON progress_progressupdate(is_active) WHERE is_active = true;",
                
                # CostLine indexes
                "CREATE INDEX IF NOT EXISTS idx_costline_plan_item ON progress_costline(plan_item_id);",
                "CREATE INDEX IF NOT EXISTS idx_costline_type ON progress_costline(cost_type);",
                "CREATE INDEX IF NOT EXISTS idx_costline_funding ON progress_costline(funding_source);",
                "CREATE INDEX IF NOT EXISTS idx_costline_period ON progress_costline(cost_period_start, cost_period_end);",
                "CREATE INDEX IF NOT EXISTS idx_costline_active ON progress_costline(is_active) WHERE is_active = true;",
                
                # UserProfile indexes
                "CREATE INDEX IF NOT EXISTS idx_userprofile_role ON accounts_userprofile(primary_role);",
                "CREATE INDEX IF NOT EXISTS idx_userprofile_department ON accounts_userprofile(department);",
                "CREATE INDEX IF NOT EXISTS idx_userprofile_active ON accounts_userprofile(is_active_user) WHERE is_active_user = true;",
                "CREATE INDEX IF NOT EXISTS idx_userprofile_manager ON accounts_userprofile(line_manager_id);",
                
                # AuditLog indexes (already defined in model but ensuring they exist)
                "CREATE INDEX IF NOT EXISTS idx_auditlog_user_timestamp ON accounts_auditlog(user_id, timestamp);",
                "CREATE INDEX IF NOT EXISTS idx_auditlog_model_object ON accounts_auditlog(model_name, object_id);",
                "CREATE INDEX IF NOT EXISTS idx_auditlog_action_timestamp ON accounts_auditlog(action, timestamp);",
                
                # Attachment indexes
                "CREATE INDEX IF NOT EXISTS idx_attachment_plan_item ON reports_attachment(linked_plan_item_id);",
                "CREATE INDEX IF NOT EXISTS idx_attachment_progress ON reports_attachment(linked_progress_update_id);",
                "CREATE INDEX IF NOT EXISTS idx_attachment_type ON reports_attachment(file_type);",
                "CREATE INDEX IF NOT EXISTS idx_attachment_access ON reports_attachment(access_level);",
                "CREATE INDEX IF NOT EXISTS idx_attachment_uploaded_by ON reports_attachment(uploaded_by_id);",
                "CREATE INDEX IF NOT EXISTS idx_attachment_active ON reports_attachment(is_active) WHERE is_active = true;",
                
                # ReportRequest indexes
                "CREATE INDEX IF NOT EXISTS idx_reportrequest_user ON reports_reportrequest(requested_by_id);",
                "CREATE INDEX IF NOT EXISTS idx_reportrequest_template ON reports_reportrequest(template);",
                "CREATE INDEX IF NOT EXISTS idx_reportrequest_status ON reports_reportrequest(status);",
                "CREATE INDEX IF NOT EXISTS idx_reportrequest_scheduled ON reports_reportrequest(is_scheduled, next_run_date);",
                "CREATE INDEX IF NOT EXISTS idx_reportrequest_created ON reports_reportrequest(created_at);",
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    # Extract index name from SQL for logging
                    index_name = index_sql.split('idx_')[1].split(' ')[0] if 'idx_' in index_sql else 'unknown'
                    self.stdout.write(f'  Created index: idx_{index_name}')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Failed to create index: {str(e)}')
                    )
        
        self.stdout.write(self.style.SUCCESS('Database indexes created successfully!'))
