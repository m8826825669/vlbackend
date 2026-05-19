"""
Seeds the database with all 6 products that the frontend's fallback catalog
expects. Pricing, descriptions, and plans match the data in:
    frontend/src/app/products/[slug]/page.tsx (FALLBACK_CATALOG)
    frontend/src/app/products/page.tsx        (FALLBACK)

Usage:
    python manage.py seed_products
    python manage.py seed_products --flush   # delete & rebuild everything

Idempotent: re-running updates existing rows in place.
"""
from django.core.management.base import BaseCommand
from apps.products.models import Category, Product, PricingPlan, Testimonial


class Command(BaseCommand):
    help = 'Seed all Vexen Labs products, pricing plans, and testimonials'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all existing products before seeding',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write(self.style.WARNING('Flushing existing products…'))
            Testimonial.objects.all().delete()
            PricingPlan.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()

        self.stdout.write('Seeding categories…')

        # ─── Categories ──────────────────────────────────────────────────
        cats = {}
        for slug, name, icon in [
            ('education',  'Education',             '🏫'),
            ('healthcare', 'Healthcare',            '🏥'),
            ('finance',    'Finance & Accounting',  '📊'),
            ('hr',         'HR & Payroll',          '👥'),
            ('gaming',     'Gaming & Sports',       '🎮'),
        ]:
            cat, _ = Category.objects.update_or_create(
                slug=slug, defaults={'name': name, 'icon': icon}
            )
            cats[slug] = cat

        self.stdout.write('Seeding products…')

        PRODUCTS = [
            # ─── 1. School Management ERP ────────────────────────────────
            {
                'slug': 'school-erp', 'emoji': '🏫',
                'name': 'School Management ERP',
                'category': cats['education'],
                'tagline': 'Run an entire school from one screen.',
                'description': (
                    'Complete school administration in one desktop app — from '
                    'admissions to alumni records. Built for Indian schools '
                    'with offline-first reliability, GST-ready fee management, '
                    'and zero monthly fees.'
                ),
                'features': [
                    {'icon': 'users',    'title': 'Student Lifecycle',  'desc': 'Admissions, transfer certificates, alumni — every student record from entry to exit.'},
                    {'icon': 'calendar', 'title': 'Attendance Tracking','desc': 'Class-wise daily attendance with biometric and QR integration support.'},
                    {'icon': 'wallet',   'title': 'Fee Management',     'desc': 'Custom fee structures, GST invoices, partial payments, due reminders.'},
                    {'icon': 'award',    'title': 'Exam & Marks',       'desc': 'Configurable grading, report cards, CBSE/ICSE/State board templates.'},
                    {'icon': 'book',     'title': 'Library Module',     'desc': 'Book catalog, issue-return, fines, member cards with barcode scanning.'},
                    {'icon': 'clock',    'title': 'Timetable Builder',  'desc': 'Drag-drop class timetables with conflict detection and teacher schedules.'},
                ],
                'tech_stack': ['Admissions', 'Attendance', 'Fees', 'Library', 'Exams', 'Timetable'],
                'requirements': {
                    'os': 'Windows 10 / 11 (64-bit)',
                    'ram': '4 GB minimum, 8 GB recommended',
                    'disk': '500 MB free space',
                    'other': 'Internet required only for license activation',
                },
                'platform': 'windows', 'version': '1.0.0', 'file_size': '48 MB',
                'is_featured': False, 'sort_order': 1,
                'rating': '4.9', 'rating_count': 87,
                'plans': [
                    {'name': 'Starter',      'price': '4999',  'max_devices': 1,  'is_popular': False,
                     'features_included': ['Up to 200 students', 'Single device license', '1 year free updates', 'Email support']},
                    {'name': 'Professional', 'price': '9999',  'max_devices': 3,  'is_popular': True,
                     'features_included': ['Unlimited students', '3 device licenses', '2 years free updates', 'Priority support', 'Biometric integration', 'Custom report cards']},
                    {'name': 'Enterprise',   'price': '19999', 'max_devices': 10, 'is_popular': False,
                     'features_included': ['Unlimited everything', '10 device licenses', 'Lifetime updates', 'Dedicated support', 'Custom branding', 'On-site training (NCR only)']},
                ],
                'testimonials': [
                    {'author_name': 'Rajesh Sharma', 'author_role': 'Principal', 'author_company': "St. Mary's School, Ghaziabad",
                     'content': "We switched from a subscription tool that cost us ₹3000/month. One-time payment and the software is faster than what we were using.", 'rating': 5},
                    {'author_name': 'Priya Mehta', 'author_role': 'Admin', 'author_company': 'Brilliant Coaching Center',
                     'content': 'Fee collection used to be our biggest headache. Now parents pay online and receipts go out automatically.', 'rating': 5},
                ],
            },

            # ─── 2. Clinic Manager Pro ───────────────────────────────────
            {
                'slug': 'clinic-manager', 'emoji': '🏥',
                'name': 'Clinic Manager Pro',
                'category': cats['healthcare'],
                'tagline': 'Your clinic, fully digital. Finally.',
                'description': (
                    'Patient records, SOAP notes, e-prescriptions, appointments, '
                    'and GST billing — built for Indian clinics with ABHA '
                    'integration and complete offline reliability.'
                ),
                'features': [
                    {'icon': 'users',    'title': 'Patient Records',  'desc': 'Complete medical history, allergies, vitals, and visit logs — all searchable.'},
                    {'icon': 'book',     'title': 'SOAP Notes',       'desc': 'Structured Subjective-Objective-Assessment-Plan templates by specialty.'},
                    {'icon': 'award',    'title': 'E-Prescriptions',  'desc': 'Drug database with brand-generic mapping, dosage helpers, and print templates.'},
                    {'icon': 'calendar', 'title': 'Appointment Scheduler', 'desc': 'Drag-drop calendar with SMS reminders and double-booking prevention.'},
                    {'icon': 'wallet',   'title': 'GST Billing',      'desc': 'Consultation, procedure, and package billing with proper HSN/SAC codes.'},
                    {'icon': 'clock',    'title': 'ABHA Integration', 'desc': 'Link patient records with their Ayushman Bharat Health Account.'},
                ],
                'tech_stack': ['OPD', 'Prescriptions', 'Billing', 'ABHA', 'SOAP Notes'],
                'requirements': {
                    'os': 'Windows 10 / 11 (64-bit)',
                    'ram': '4 GB minimum, 8 GB recommended',
                    'disk': '1 GB free space',
                    'other': 'Internet for license activation and optional cloud sync',
                },
                'platform': 'windows', 'version': '1.2.0', 'file_size': '62 MB',
                'is_featured': True, 'sort_order': 2,
                'rating': '4.8', 'rating_count': 54,
                'plans': [
                    {'name': 'Solo',         'price': '7999',  'max_devices': 1,  'is_popular': False,
                     'features_included': ['Single doctor', '1 device license', '1 year updates', 'Email support']},
                    {'name': 'Clinic',       'price': '14999', 'max_devices': 3,  'is_popular': True,
                     'features_included': ['Up to 5 doctors', '3 device licenses', '2 years updates', 'Priority support', 'WhatsApp reminders', 'Custom templates']},
                    {'name': 'Multi-Branch', 'price': '29999', 'max_devices': 10, 'is_popular': False,
                     'features_included': ['Unlimited doctors', '10 devices', 'Lifetime updates', 'Dedicated support', 'Multi-location sync', 'On-site training']},
                ],
                'testimonials': [
                    {'author_name': 'Dr. Anita Kapoor', 'author_role': 'GP', 'author_company': 'Wellness Clinic, Noida',
                     'content': 'Switched from a fancy SaaS that kept charging me more every year. This pays for itself in 4 months.', 'rating': 5},
                    {'author_name': 'Dr. Vikram Singh', 'author_role': 'Dentist', 'author_company': 'Smile Studio',
                     'content': 'The SOAP templates saved me hours each week. Prescription printing is finally professional.', 'rating': 5},
                ],
            },

            # ─── 3. Medical Store ERP ────────────────────────────────────
            {
                'slug': 'medical-store', 'emoji': '💊',
                'name': 'Medical Store ERP',
                'category': cats['healthcare'],
                'tagline': 'Smarter inventory. Zero wastage.',
                'description': (
                    'FEFO inventory, GST billing, expiry alerts, barcode scanning, '
                    'and a fast counter POS — purpose-built for Indian pharmacies.'
                ),
                'features': [
                    {'icon': 'wallet',   'title': 'FEFO Allocation',    'desc': 'First-Expiry-First-Out batch picking prevents stale stock from sitting on shelves.'},
                    {'icon': 'clock',    'title': 'Expiry Alerts',      'desc': 'Configurable warnings 30/60/90 days before expiry with returns workflow.'},
                    {'icon': 'award',    'title': 'Barcode + POS',      'desc': 'Fast counter checkout with barcode scanning and strip-unit conversion.'},
                    {'icon': 'users',    'title': 'GST Billing',        'desc': 'CGST/SGST/IGST handling with HSN codes and GSTR-1 export.'},
                    {'icon': 'book',     'title': 'Drug License Tracking', 'desc': 'Maintain DL numbers per supplier with auto-renewal reminders.'},
                    {'icon': 'calendar', 'title': 'Reorder Suggestions','desc': 'Algorithm suggests reorder quantities based on velocity.'},
                ],
                'tech_stack': ['FEFO', 'GST', 'Barcode', 'POS', 'Inventory'],
                'requirements': {
                    'os': 'Windows 10 / 11 (64-bit)',
                    'ram': '4 GB minimum',
                    'disk': '500 MB free space',
                    'other': 'USB barcode scanner recommended for counter use',
                },
                'platform': 'windows', 'version': '1.1.0', 'file_size': '38 MB',
                'is_featured': False, 'sort_order': 3,
                'rating': '4.7', 'rating_count': 43,
                'demo_video_url': 'https://demo.vexenlabs.com/medical-store',
                'plans': [
                    {'name': 'Single Counter', 'price': '3499',  'max_devices': 1,  'is_popular': False,
                     'features_included': ['1 counter', 'Up to 5,000 SKUs', '1 year updates', 'Email support']},
                    {'name': 'Multi-Counter',  'price': '8999',  'max_devices': 3,  'is_popular': True,
                     'features_included': ['Up to 3 counters', 'Unlimited SKUs', '2 years updates', 'Priority support', 'Barcode label printing']},
                    {'name': 'Chain',          'price': '19999', 'max_devices': 10, 'is_popular': False,
                     'features_included': ['10 counters', 'Multi-store sync', 'Lifetime updates', 'Dedicated support', 'Analytics dashboard']},
                ],
                'testimonials': [
                    {'author_name': 'Amit Goel', 'author_role': 'Owner', 'author_company': 'Goel Medical Store',
                     'content': 'FEFO has saved us from at least ₹50,000 in expired stock this year alone.', 'rating': 5},
                ],
            },

            # ─── 4. BharatBooks Accounting ───────────────────────────────
            {
                'slug': 'accounting', 'emoji': '📊',
                'name': 'BharatBooks Accounting',
                'category': cats['finance'],
                'tagline': 'Accounting without the accountant fees.',
                'description': (
                    'GST invoicing, P&L reports, bank reconciliation, GSTR exports — '
                    'the no-nonsense Tally alternative for Indian SMBs.'
                ),
                'features': [
                    {'icon': 'wallet',   'title': 'GST Invoicing',     'desc': 'Generate compliant tax invoices with CGST/SGST/IGST and HSN codes.'},
                    {'icon': 'book',     'title': 'Double-Entry Ledger','desc': 'Full double-entry bookkeeping with chart of accounts and journal entries.'},
                    {'icon': 'award',    'title': 'P&L + Balance Sheet','desc': 'Live financial reports — drill down from totals to individual entries.'},
                    {'icon': 'calendar', 'title': 'Bank Reconciliation','desc': 'Import bank statements (CSV/PDF) and auto-match transactions.'},
                    {'icon': 'users',    'title': 'GSTR-1 / 3B Export','desc': 'One-click export of returns in JSON format ready for the GST portal.'},
                    {'icon': 'clock',    'title': 'Multi-Currency',    'desc': 'Invoice in foreign currency with auto exchange rate from RBI reference rates.'},
                ],
                'tech_stack': ['GST', 'Invoicing', 'P&L', 'GSTR', 'Bank Recon'],
                'requirements': {
                    'os': 'Windows 10 / 11 (64-bit), macOS 12+',
                    'ram': '4 GB minimum',
                    'disk': '500 MB free space',
                    'other': 'No internet required after activation',
                },
                'platform': 'all', 'version': '2.0.0', 'file_size': '32 MB',
                'is_featured': False, 'sort_order': 4,
                'rating': '4.6', 'rating_count': 31,
                'plans': [
                    {'name': 'Basic',        'price': '2999',  'max_devices': 1,  'is_popular': False,
                     'features_included': ['1 company', '1 user', '1 year updates']},
                    {'name': 'Professional', 'price': '5999',  'max_devices': 3,  'is_popular': True,
                     'features_included': ['Up to 3 companies', '3 users', '2 years updates', 'Priority support']},
                    {'name': 'Business',     'price': '11999', 'max_devices': 10, 'is_popular': False,
                     'features_included': ['Unlimited companies', '10 users', 'Lifetime updates', 'Dedicated support']},
                ],
                'testimonials': [
                    {'author_name': 'Sunita Verma', 'author_role': 'Founder', 'author_company': 'Verma Traders',
                     'content': 'I was paying ₹999/month for invoicing software. BharatBooks paid for itself in 3 months.', 'rating': 5},
                ],
            },

            # ─── 5. HRMS Pro ─────────────────────────────────────────────
            {
                'slug': 'hrms', 'emoji': '👥',
                'name': 'HRMS Pro',
                'category': cats['hr'],
                'tagline': 'Happy teams start with great HR software.',
                'description': (
                    'Recruitment, payroll, attendance, leaves, and appraisals — '
                    'complete HR in one desktop app, designed for Indian compliance.'
                ),
                'features': [
                    {'icon': 'users',    'title': 'Employee Records',  'desc': 'Complete employee master with documents, statutory IDs, and bank details.'},
                    {'icon': 'wallet',   'title': 'Payroll Engine',    'desc': 'Automated PF, ESI, PT, TDS calculation with Form 16 and salary slips.'},
                    {'icon': 'calendar', 'title': 'Leave Management',  'desc': 'Custom leave types, balances, calendar view, and approval workflows.'},
                    {'icon': 'clock',    'title': 'Attendance',        'desc': 'Biometric/RFID integration, shift management, and overtime tracking.'},
                    {'icon': 'award',    'title': 'Recruitment',       'desc': 'Job postings, applicant tracking, interview scheduling, and offer letters.'},
                    {'icon': 'book',     'title': 'Appraisals',        'desc': 'Configurable performance review cycles with self/manager/peer feedback.'},
                ],
                'tech_stack': ['Payroll', 'Recruitment', 'Leaves', 'PF/ESI', 'Appraisals'],
                'requirements': {
                    'os': 'Windows 10 / 11 (64-bit)',
                    'ram': '8 GB recommended',
                    'disk': '1 GB free space',
                    'other': 'Network access for multi-device sync (Growth+ plans)',
                },
                'platform': 'windows', 'version': '1.0.0', 'file_size': '55 MB',
                'is_featured': False, 'sort_order': 5,
                'rating': '4.5', 'rating_count': 22,
                'plans': [
                    {'name': 'Starter',    'price': '5999',  'max_devices': 1,  'is_popular': False,
                     'features_included': ['Up to 25 employees', '1 device', '1 year updates']},
                    {'name': 'Growth',     'price': '11999', 'max_devices': 3,  'is_popular': True,
                     'features_included': ['Up to 100 employees', '3 devices', '2 years updates', 'Priority support']},
                    {'name': 'Enterprise', 'price': '24999', 'max_devices': 10, 'is_popular': False,
                     'features_included': ['Up to 250 employees', '10 devices', 'Lifetime updates', 'Dedicated support', 'Custom workflows']},
                ],
                'testimonials': [],
            },

            # ─── 6. Fantasy Sports Platform ──────────────────────────────
            {
                'slug': 'fantasy-sports', 'emoji': '🏏',
                'name': 'Fantasy Sports Platform',
                'category': cats['gaming'],
                'tagline': 'Launch your own fantasy sports empire.',
                'description': (
                    'Full-stack fantasy sports platform: real-time scoring, wallet, '
                    'KYC, UPI payments — ready to launch your Dream11 competitor.'
                ),
                'features': [
                    {'icon': 'clock',    'title': 'Real-time Scoring', 'desc': 'Live cricket/football scoring with sub-second leaderboard updates.'},
                    {'icon': 'wallet',   'title': 'Wallet & Payouts',  'desc': 'In-app wallet, UPI deposits, RTGS/IMPS withdrawals with auto-reconciliation.'},
                    {'icon': 'users',    'title': 'KYC Workflow',      'desc': 'PAN/Aadhaar verification with manual review queue and AML flags.'},
                    {'icon': 'award',    'title': 'Contest Builder',   'desc': 'Public, private, head-to-head, and mega contests with custom prize structures.'},
                    {'icon': 'book',     'title': 'Admin Dashboard',   'desc': 'Live ops view: active users, contest fill rates, revenue, fraud signals.'},
                    {'icon': 'calendar', 'title': 'Notifications',     'desc': 'Push, SMS, email engines with templated campaigns and triggered messages.'},
                ],
                'tech_stack': ['Real-time', 'Wallet', 'KYC', 'UPI', 'Contest'],
                'requirements': {
                    'os': 'Linux server (Ubuntu 22.04+ recommended)',
                    'ram': '8 GB+ for production',
                    'disk': '50 GB SSD',
                    'other': 'PostgreSQL 14+, Redis 7+, Node.js 20+',
                },
                'platform': 'linux', 'version': '1.0.0', 'file_size': '120 MB',
                'is_featured': False, 'sort_order': 6,
                'rating': '4.8', 'rating_count': 12,
                'plans': [
                    {'name': 'Source License', 'price': '29999', 'max_devices': 1, 'is_popular': True,
                     'features_included': ['Full source code', '1 deployment', 'Self-hosted', '3 months support']},
                    {'name': 'Managed Setup',  'price': '79999', 'max_devices': 1, 'is_popular': False,
                     'features_included': ['Source + deployment', 'Custom branding', '6 months support', '5 enhancement requests']},
                ],
                'testimonials': [],
            },
        ]

        for pd in PRODUCTS:
            testimonials_data = pd.pop('testimonials', [])
            plans_data = pd.pop('plans', [])

            product, created = Product.objects.update_or_create(
                slug=pd['slug'], defaults=pd
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action}: {product.name}')

            # Plans
            PricingPlan.objects.filter(product=product).delete()
            for i, plan in enumerate(plans_data):
                PricingPlan.objects.create(
                    product=product,
                    sort_order=i,
                    billing_cycle='one_time',
                    max_users=plan.get('max_devices', 1),
                    **plan,
                )

            # Testimonials
            Testimonial.objects.filter(product=product).delete()
            for t in testimonials_data:
                Testimonial.objects.create(product=product, is_featured=True, **t)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Seeded {len(PRODUCTS)} products across {len(cats)} categories.'
        ))
