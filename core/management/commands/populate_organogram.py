"""
Management command to populate the database with the complete organizational structure
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from datetime import date, datetime
from core.models import OrgUnit, Staff
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Populate the database with the complete organizational structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing organizational data before populating',
        )

    def handle(self, *args, **options):
        if options['clear_existing']:
            self.stdout.write('Clearing existing organizational data...')
            with transaction.atomic():
                Staff.objects.all().delete()
                OrgUnit.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write('Creating organizational structure...')
        
        with transaction.atomic():
            # Create organizational units
            org_units = self.create_org_units()
            
            # Create staff members
            self.create_staff_members(org_units)
            
            # Link users to staff members where possible
            self.link_users_to_staff()

        self.stdout.write(self.style.SUCCESS('Organizational structure created successfully!'))

    def create_org_units(self):
        """Create all organizational units"""
        org_units = {}
        
        # CEO Office
        ceo_office = OrgUnit.objects.create(
            name="Office of CEO",
            unit_type="CEO_OFFICE",
            parent=None
        )
        org_units['CEO_OFFICE'] = ceo_office
        
        # Chief Directorate: Human Capital Development
        hcd = OrgUnit.objects.create(
            name="Chief Directorate: Human Capital Development",
            unit_type="CHIEF_DIRECTORATE",
            parent=None
        )
        org_units['HCD'] = hcd

        # Chief Directorate: Public Sector Development (currently no Chief Director)
        psd = OrgUnit.objects.create(
            name="Chief Directorate: Public Sector Development",
            unit_type="CHIEF_DIRECTORATE",
            parent=None
        )
        org_units['PSD'] = psd
        
        # Directorates under HCD
        hcd_directorates = [
            ("Directorate: Vocational Development Programme (VDP)", "VDP"),
            ("Directorate: Talent Management (TM)", "TM"),
            ("Directorate: ETQA", "ETQA")
        ]

        for dir_name, dir_code in hcd_directorates:
            org_unit = OrgUnit.objects.create(
                name=dir_name,
                unit_type="DIRECTORATE",
                parent=hcd
            )
            org_units[dir_code] = org_unit

        # Directorates under Public Sector Development
        psd_directorates = [
            ("Directorate: Integrated Management & Leadership Development Strategy (IMLDS)", "IMLDS"),
            ("Directorate: Programme Management", "PM")
        ]

        for dir_name, dir_code in psd_directorates:
            org_unit = OrgUnit.objects.create(
                name=dir_name,
                unit_type="DIRECTORATE",
                parent=psd
            )
            org_units[dir_code] = org_unit
        
        # Sub-directorates/Units
        sub_units = [
            # Under HCD directorates
            ("Bursaries Unit", "BURSARIES", "TM"),
            ("M&E Unit", "ME", "ETQA"),
            ("QALA Unit", "QALA", "ETQA"),
            ("Workforce Development Unit", "WDU", "TM"),
            ("Integrated Workplace Learning (IWL) Unit", "IWL", "ETQA"),
            # Under PSD directorates
            ("Design and Planning Unit", "DPU", "IMLDS"),
            ("Implementation Unit", "IU", "IMLDS")
        ]
        
        for unit_name, unit_code, parent_code in sub_units:
            org_unit = OrgUnit.objects.create(
                name=unit_name,
                unit_type="SUB_DIRECTORATE",
                parent=org_units[parent_code]
            )
            org_units[unit_code] = org_unit
        
        self.stdout.write(f'Created {len(org_units)} organizational units.')
        return org_units

    def create_staff_members(self, org_units):
        """Create all staff members"""
        staff_data = [
            # CEO
            {
                'name': 'China Mashinini',
                'title': 'CEO',
                'unit': 'CEO_OFFICE',
                'level': 'LEVEL_16',  # Director-General level
                'is_manager': True,
                'persal': 'CEO001'
            },

            # Office of CEO
            {
                'name': 'Bellina Molaba',
                'title': 'DD: Office of CEO',
                'unit': 'CEO_OFFICE',
                'level': 'LEVEL_12',  # Deputy Director
                'is_manager': True,
                'persal': 'CEO002'
            },
            {
                'name': 'Israel Matjila',
                'title': 'Messenger: Office of CEO',
                'unit': 'CEO_OFFICE',
                'level': 'LEVEL_3',
                'persal': 'CEO003'
            },
            {
                'name': 'Adelaide Manokoane',
                'title': 'SAC: Office of CEO',
                'unit': 'CEO_OFFICE',
                'level': 'LEVEL_5',
                'persal': 'CEO004'
            },
            {
                'name': 'Muzi Melani',
                'title': 'Clerk: Office of CEO',
                'unit': 'CEO_OFFICE',
                'level': 'LEVEL_4',
                'persal': 'CEO005'
            },

            # HCD Leadership
            {
                'name': 'Lydia Phehla',
                'title': 'Acting Chief Director: HCD',
                'unit': 'HCD',
                'level': 'LEVEL_14',  # Chief Director
                'is_manager': True,
                'persal': 'HCD001'
            },
            {
                'name': 'Lerato Ntoahae',
                'title': 'PA',
                'unit': 'HCD',
                'level': 'LEVEL_6',
                'persal': 'HCD002'
            },
            {
                'name': 'Ndibulele Poswa',
                'title': 'PA: CD HCD',
                'unit': 'HCD',
                'level': 'LEVEL_6',
                'persal': 'HCD003'
            },
        ]
        
        # Add VDP staff
        vdp_staff = [
            ('Mologadi Matseba', 'Director: VDP', 'LEVEL_13', True, 'VDP001'),  # Director
            ('Kenneth Baloi', 'DD', 'LEVEL_12', True, 'VDP002'),  # Deputy Director
            ('Karabo Moseneke', 'SAO: VDP', 'LEVEL_7', False, 'VDP003'),  # Senior Admin Officer
            ('Jolene Pinto', 'DD: VDP', 'LEVEL_12', True, 'VDP004'),  # Deputy Director
            ('Ntsoaki Maseko', 'PA: Director VDP', 'LEVEL_6', False, 'VDP005'),  # Personal Assistant
            ('Rodgers Malungane', 'ASD: VDP', 'LEVEL_10', False, 'VDP006'),  # Assistant Director
            ('Takalane Mmbangeni', 'SAC', 'LEVEL_5', False, 'VDP007'),  # Senior Admin Clerk
        ]
        
        for name, title, level, is_mgr, persal in vdp_staff:
            staff_data.append({
                'name': name,
                'title': title,
                'unit': 'VDP',
                'level': level,
                'is_manager': is_mgr,
                'persal': persal
            })
        
        # Add TM staff
        tm_staff = [
            ('Kgabo Morifi', 'Director: TM', 'LEVEL_13', True, 'TM001'),  # Director
            ('Mogopa Ngcobo', 'SAO: TM', 'LEVEL_7', False, 'TM002'),  # Senior Admin Officer
            ('Thabilsile Ngubane', 'DD: TM', 'LEVEL_12', True, 'TM003'),  # Deputy Director
            ('Mbongeni Mtshali', 'ASD: TM', 'LEVEL_10', False, 'TM004'),  # Assistant Director
            ('Jane Seshoka', 'SAO: TM', 'LEVEL_7', False, 'TM005'),  # Senior Admin Officer
            ('Dimpho Masokela', 'SAC: TM', 'LEVEL_5', False, 'TM006'),  # Senior Admin Clerk
            ('Elizabeth Tladi', 'SAO: TM', 'LEVEL_7', False, 'TM007'),  # Senior Admin Officer
            ('Zanele Ncala', 'SAO: TM', 'LEVEL_7', False, 'TM008'),  # Senior Admin Officer
            ('Innocentia Marule', 'DD: TM', 'LEVEL_12', True, 'TM009'),  # Deputy Director
            ('Ruudyguilty Mnisi', 'ASD: TM', 'LEVEL_9', False, 'TM010'),  # Assistant Director
            ('Ntombifuthi Mafafo', 'ASD: TM', 'LEVEL_9', False, 'TM011'),  # Assistant Director
            ('Ayanda Moses', 'SAO: TM', 'LEVEL_7', False, 'TM012'),  # Senior Admin Officer
            ('Lorraine Moloi', 'SAC: TM', 'LEVEL_5', False, 'TM013'),  # Senior Admin Clerk
            ('Moeder kesi', 'SAC: TM', 'LEVEL_5', False, 'TM014'),  # Senior Admin Clerk
            ('Khazamula Mabasa', 'SAO: TM', 'LEVEL_7', False, 'TM015'),  # Senior Admin Officer
            ('Precious Manale', 'SAC: TM', 'LEVEL_5', False, 'TM016'),  # Senior Admin Clerk
            ('Simon Nkontlha', 'ASD: TM', 'LEVEL_9', False, 'TM017'),  # Assistant Director
            ('Jabulani Tshabalala', 'SAC: TM', 'LEVEL_5', False, 'TM018'),  # Senior Admin Clerk
            ('Niza Mathonsi', 'SAC: TM', 'LEVEL_5', False, 'TM019'),  # Senior Admin Clerk
            ('Mmuso Tsimong', 'SAC: TM', 'LEVEL_5', False, 'TM020'),  # Senior Admin Clerk
            ('Kenneth Radebe', 'SAC: TM', 'LEVEL_5', False, 'TM021'),  # Senior Admin Clerk
        ]
        
        for name, title, level, is_mgr, persal in tm_staff:
            staff_data.append({
                'name': name,
                'title': title,
                'unit': 'TM',
                'level': level,
                'is_manager': is_mgr,
                'persal': persal
            })

        # Add ETQA staff
        etqa_staff = [
            ('Amuzweni Ngoma', 'Director: ETQA', 'LEVEL_13', True, 'ETQA001'),  # Director
            ('Phetheni Mathopa', 'PA: Director ETQA', 'LEVEL_6', False, 'ETQA002'),  # Personal Assistant
            ('Veronica Lesejane', 'PA: Corporate Services', 'LEVEL_6', False, 'ETQA003'),  # Personal Assistant
            ('Nomakhosazana Nkosi', 'PA', 'LEVEL_6', False, 'ETQA004'),  # Personal Assistant
            ('David Moremi', 'ASD: ETQA', 'LEVEL_10', False, 'ETQA005'),  # Assistant Director
            ('Sadike Emily', 'DD: ETQA', 'LEVEL_12', True, 'ETQA006'),  # Deputy Director
            ('Ngwako Mohale', 'SAO: ETQA', 'LEVEL_7', False, 'ETQA007'),  # Senior Admin Officer
            ('Vincent Sithole', 'ASD: ETQA', 'LEVEL_9', False, 'ETQA008'),  # Assistant Director
            ('LeighAnn Du Toit', 'ASD: ETQA', 'LEVEL_9', False, 'ETQA009'),  # Assistant Director
            ('Mamang Mokone', 'DD: ETQA', 'LEVEL_12', True, 'ETQA010'),  # Deputy Director
            ('Tebogo Mojapelo', 'SAO: ETQA', 'LEVEL_7', False, 'ETQA011'),  # Senior Admin Officer
            ('Khutso Ntsewa', 'ASD: ETQA', 'LEVEL_9', False, 'ETQA012'),  # Assistant Director
            ('Mathope Mphulanyane', 'ASD: ETQA', 'LEVEL_10', False, 'ETQA013'),  # Assistant Director
            ('Anna Mathebula', 'SAC: ILMDS', 'LEVEL_5', False, 'ETQA014'),  # Senior Admin Clerk
            ('Alistair Johanson', 'DD: IWL', 'LEVEL_12', True, 'ETQA015'),  # Deputy Director
            ('Affectionate Ubisi', 'ASD: IWL', 'LEVEL_9', False, 'ETQA016'),  # Assistant Director
            ('Lynn Benade', 'ASD: IWL', 'LEVEL_10', False, 'ETQA017'),  # Assistant Director
            ('Nozipho Nhlapo', 'ASD: IWL', 'LEVEL_9', False, 'ETQA018'),  # Assistant Director
        ]

        for name, title, level, is_mgr, persal in etqa_staff:
            staff_data.append({
                'name': name,
                'title': title,
                'unit': 'ETQA',
                'level': level,
                'is_manager': is_mgr,
                'persal': persal
            })

        # Add IMLDS staff (under Public Sector Development)
        imlds_staff = [
            ('Jurgens Hanekom', 'Director: IMLDS', 'LEVEL_13', True, 'IMLDS001'),  # Director
            ('Winnie Miya', 'PA: Director IMLDS', 'LEVEL_6', False, 'IMLDS002'),  # Personal Assistant
            ('Veronica Lesejane', 'PA: Corporate Services', 'LEVEL_6', False, 'IMLDS003'),  # Personal Assistant
            ('Nomakhosazana Nkosi', 'PA', 'LEVEL_6', False, 'IMLDS004'),  # Personal Assistant
            # Design and Planning Unit
            ('Zelly Hlungwani', 'DD: IMLDS', 'LEVEL_12', True, 'IMLDS005'),  # Deputy Director
            ('Mashudu Mabuda', 'ASD: IMLDS', 'LEVEL_10', False, 'IMLDS006'),  # Assistant Director
            ('Nolitha Notyesi', 'SAO: IMLDS', 'LEVEL_7', False, 'IMLDS007'),  # Senior Admin Officer
            ('Debby Mmeko', 'ASD: IMLDS', 'LEVEL_10', False, 'IMLDS008'),  # Assistant Director
            # Implementation Unit
            ('Andre Erens', 'ASD: IMLDS', 'LEVEL_10', False, 'IMLDS009'),  # Assistant Director
            ('Pule Motjopi', 'ASD: IMLDS', 'LEVEL_9', False, 'IMLDS010'),  # Assistant Director
            ('Lindiwe Radebe', 'CAO', 'LEVEL_4', False, 'IMLDS011'),  # Chief Admin Officer
        ]

        for name, title, level, is_mgr, persal in imlds_staff:
            staff_data.append({
                'name': name,
                'title': title,
                'unit': 'IMLDS',
                'level': level,
                'is_manager': is_mgr,
                'persal': persal
            })

        # Add Programme Management staff (under Public Sector Development)
        pm_staff = [
            ('Oduetse Motsage', 'DD: PM', 'LEVEL_12', True, 'PM001'),  # Deputy Director
            ('Cecile Malgas', 'DD: PM', 'LEVEL_12', True, 'PM002'),  # Deputy Director
            ('Sibusiso Xaba', 'ASD: PM', 'LEVEL_10', False, 'PM003'),  # Assistant Director
            ('Ntombi Mtambeki', 'ASD: PM', 'LEVEL_10', False, 'PM004'),  # Assistant Director
            ('Zandile Dangwana', 'ASD: PM', 'LEVEL_9', False, 'PM005'),  # Assistant Director
            ('Lindiwe Motshawe', 'ASD: PM', 'LEVEL_10', False, 'PM006'),  # Assistant Director
            ('Suraya Tack', 'SAC: PM', 'LEVEL_5', False, 'PM007'),  # Senior Admin Clerk
            ('Stanley Butane', 'ASD: PM', 'LEVEL_9', False, 'PM008'),  # Assistant Director
            ('Stephen Ramafoko', 'ASD: PM', 'LEVEL_10', False, 'PM009'),  # Assistant Director
            ('Khayalethu Dweba', 'ASD: PM', 'LEVEL_9', False, 'PM010'),  # Assistant Director
            ('Tinyiko Ntusi', 'ASD: PM', 'LEVEL_9', False, 'PM011'),  # Assistant Director
            ('Lerato Ramsey', 'ASD: PM', 'LEVEL_10', False, 'PM012'),  # Assistant Director
            ('Hamilton Kali', 'ASD: PM', 'LEVEL_9', False, 'PM013'),  # Assistant Director
            ('Puseletso Mohosho', 'ASD: PM', 'LEVEL_9', False, 'PM014'),  # Assistant Director
            ('Vusumuzi Nkosi', 'Data Typist', 'LEVEL_4', False, 'PM015'),  # Data Typist
        ]

        for name, title, level, is_mgr, persal in pm_staff:
            staff_data.append({
                'name': name,
                'title': title,
                'unit': 'PM',
                'level': level,
                'is_manager': is_mgr,
                'persal': persal
            })
        
        # Create staff members
        created_count = 0
        seen_emails = set()
        for staff_info in staff_data:
            first_name, last_name = self.parse_name(staff_info['name'])
            email = self.generate_email(first_name, last_name)

            # Check for duplicate emails and add number if needed
            original_email = email
            counter = 1
            while email in seen_emails:
                name_part = original_email.split('@')[0]
                domain_part = original_email.split('@')[1]
                email = f"{name_part}{counter}@{domain_part}"
                counter += 1

            seen_emails.add(email)

            try:
                staff = Staff.objects.create(
                    persal_number=staff_info['persal'],
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    org_unit=org_units[staff_info['unit']],
                    job_title=staff_info['title'],
                    salary_level=staff_info['level'],
                    start_date=date(2020, 1, 1),  # Default start date
                    is_manager=staff_info.get('is_manager', False),
                    employment_type='PERMANENT'
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(f'Error creating staff {staff_info["name"]}: {e}')
                self.stdout.write(f'Email: {email}, PERSAL: {staff_info["persal"]}')
        
        self.stdout.write(f'Created {created_count} staff members.')

    def parse_name(self, full_name):
        """Parse full name into first and last name"""
        parts = full_name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
        else:
            first_name = parts[0] if parts else 'Unknown'
            last_name = 'Unknown'
        return first_name, last_name

    def generate_email(self, first_name, last_name):
        """Generate email address from name"""
        first = first_name.lower().replace(' ', '')
        last = last_name.lower().replace(' ', '')
        return f"{first}.{last}@example.com"

    def link_users_to_staff(self):
        """Create users for all staff members and link them properly"""
        created_count = 0
        linked_count = 0

        for staff_member in Staff.objects.all():
            # Generate username from email
            username = staff_member.email.split('@')[0]

            # Check if user already exists
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': staff_member.email,
                    'first_name': staff_member.first_name,
                    'last_name': staff_member.last_name,
                    'is_active': staff_member.is_active,
                }
            )

            if user_created:
                # Set a default password (should be changed on first login)
                user.set_password('ChangeMe123!')
                user.save()
                created_count += 1

            # Create or update user profile
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'staff_member': staff_member,
                    'employee_number': staff_member.persal_number,
                    'job_title': staff_member.job_title,
                    'department': staff_member.org_unit.name,
                    'unit_subdirectorate': staff_member.org_unit.name,
                    'primary_role': self.get_role_from_title(staff_member.job_title),
                }
            )

            # Update profile if it already existed
            if not profile_created:
                profile.staff_member = staff_member
                profile.employee_number = staff_member.persal_number
                profile.job_title = staff_member.job_title
                profile.department = staff_member.org_unit.name
                profile.unit_subdirectorate = staff_member.org_unit.name
                profile.primary_role = self.get_role_from_title(staff_member.job_title)
                profile.save()

            linked_count += 1

        self.stdout.write(f'Created {created_count} new users and linked {linked_count} staff members to user accounts.')

    def get_role_from_title(self, job_title):
        """Determine user role based on job title"""
        title_upper = job_title.upper()

        # CEO is the only true senior manager
        if 'CEO' in title_upper and 'OFFICE' not in title_upper:
            return 'SENIOR_MANAGER'
        elif 'DIRECTOR-GENERAL' in title_upper:
            return 'SENIOR_MANAGER'
        elif 'CHIEF DIRECTOR' in title_upper:
            return 'SENIOR_MANAGER'
        elif 'DIRECTOR:' in title_upper:
            return 'PROGRAMME_MANAGER'
        elif 'DD:' in title_upper or 'DEPUTY DIRECTOR' in title_upper:
            return 'PROGRAMME_MANAGER'
        elif 'ASD:' in title_upper or 'ASSISTANT DIRECTOR' in title_upper:
            return 'PROGRAMME_MANAGER'
        elif 'SAO:' in title_upper or 'SENIOR ADMINISTRATIVE' in title_upper:
            return 'ME_STRATEGY'
        # CEO Office staff (including Belina Molaba) are regular staff, not executives
        elif 'OFFICE OF CEO' in title_upper or 'CEO OFFICE' in title_upper:
            return 'ME_STRATEGY'
        else:
            return 'ME_STRATEGY'  # Default role for other staff
