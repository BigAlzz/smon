"""
Template tags for staff-related functionality
"""

from django import template

register = template.Library()


@register.filter
def position_color(job_title):
    """
    Return Bootstrap color class based on job position/title
    """
    if not job_title:
        return 'light text-dark'
    
    title = job_title.upper()
    
    # CEO/Director-General level
    if 'CEO' in title or 'DIRECTOR-GENERAL' in title:
        return 'dark'
    
    # Chief Director level
    if 'CHIEF DIRECTOR' in title:
        return 'danger'
    
    # Director level (but not Deputy Director)
    if 'DIRECTOR:' in title and 'DEPUTY' not in title:
        return 'warning'
    
    # Deputy Director level
    if 'DD:' in title or 'DEPUTY DIRECTOR' in title:
        return 'info'
    
    # Assistant Director level
    if 'ASD:' in title or 'ASSISTANT DIRECTOR' in title:
        return 'primary'
    
    # Senior Administrative Officer level
    if 'SAO:' in title or 'SENIOR ADMINISTRATIVE' in title:
        return 'success'
    
    # Personal Assistant level
    if 'PA:' in title or title == 'PA':
        return 'secondary'
    
    # Senior Administrative Clerk
    if 'SAC:' in title or 'SENIOR ADMINISTRATIVE CLERK' in title:
        return 'secondary'
    
    # Administrative Officer
    if 'ADMINISTRATIVE OFFICER' in title or 'ADMIN OFFICER' in title:
        return 'secondary'
    
    # Clerk/General positions
    if 'CLERK' in title or 'MESSENGER' in title or 'TYPIST' in title:
        return 'light text-dark'
    
    # Default for other positions
    return 'light text-dark'


@register.filter
def position_category(job_title):
    """
    Return position category for grouping
    """
    if not job_title:
        return 'Other'
    
    title = job_title.upper()
    
    if 'CEO' in title or 'DIRECTOR-GENERAL' in title:
        return 'Executive'
    elif 'CHIEF DIRECTOR' in title:
        return 'Chief Directorate'
    elif 'DIRECTOR:' in title and 'DEPUTY' not in title:
        return 'Directorate'
    elif 'DD:' in title or 'DEPUTY DIRECTOR' in title:
        return 'Deputy Directorate'
    elif 'ASD:' in title or 'ASSISTANT DIRECTOR' in title:
        return 'Assistant Directorate'
    elif 'SAO:' in title or 'SENIOR ADMINISTRATIVE' in title:
        return 'Senior Administration'
    elif 'PA:' in title or title == 'PA':
        return 'Personal Assistant'
    elif 'SAC:' in title or 'ADMINISTRATIVE' in title:
        return 'Administration'
    else:
        return 'Support Staff'


@register.simple_tag
def position_legend():
    """
    Return HTML for position color legend
    """
    legend_items = [
        ('dark', 'CEO/DG'),
        ('danger', 'Chief Director'),
        ('warning', 'Director'),
        ('info', 'Deputy Director'),
        ('primary', 'Assistant Director'),
        ('success', 'Senior Admin Officer'),
        ('secondary', 'Personal Assistant'),
        ('light text-dark', 'Other'),
    ]
    
    html = '<div class="d-flex flex-wrap gap-2">'
    for color, label in legend_items:
        html += f'<span class="badge bg-{color}">{label}</span>'
    html += '</div>'
    
    return html
