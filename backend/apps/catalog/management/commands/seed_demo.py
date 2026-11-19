from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import WorkerProfile
from apps.catalog.models import ServiceCategory, WorkerService
from apps.customers.models import CustomerProfile

User = get_user_model()

CATEGORIES = [
    ("electrician", "Electrician", "Wiring, faults, installations", 25000, 80000),
    ("plumber", "Plumber", "Leaks, geysers, drainage", 30000, 90000),
    ("cleaner", "Cleaner", "Home and office cleaning", 15000, 45000),
    ("gardener", "Gardener", "Lawn, pruning, garden care", 18000, 50000),
    ("handyman", "Handyman", "General repairs and odd jobs", 20000, 60000),
]


class Command(BaseCommand):
    help = "Seed service categories and demo customer/worker/admin accounts"

    def handle(self, *args, **options):
        for slug, name, desc, lo, hi in CATEGORIES:
            ServiceCategory.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": desc,
                    "suggested_min_cents": lo,
                    "suggested_max_cents": hi,
                },
            )

        customer, _ = User.objects.get_or_create(
            email="customer@ispan.test",
            defaults={
                "phone": "+27820000001",
                "role": User.ActiveProfile.CUSTOMER,
                "active_profile": User.ActiveProfile.CUSTOMER,
                "is_customer": True,
                "first_name": "Thandi",
                "last_name": "Molefe",
                "email_verified": True,
                "phone_verified": True,
            },
        )
        customer.set_password("password123")
        customer.is_customer = True
        customer.save()
        CustomerProfile.objects.get_or_create(user=customer)

        worker, _ = User.objects.get_or_create(
            email="worker@ispan.test",
            defaults={
                "phone": "+27820000002",
                "role": User.ActiveProfile.WORKER,
                "active_profile": User.ActiveProfile.WORKER,
                "is_customer": True,
                "is_worker": True,
                "first_name": "Sipho",
                "last_name": "Ndlovu",
                "email_verified": True,
                "phone_verified": True,
            },
        )
        worker.set_password("password123")
        worker.is_worker = True
        worker.is_customer = True
        worker.save()
        CustomerProfile.objects.get_or_create(user=worker)

        profile, _ = WorkerProfile.objects.get_or_create(
            user=worker,
            defaults={
                "display_name": "Sipho Ndlovu",
                "bio": "Licensed electrician with 8 years experience across Cape Town.",
                "verification_status": WorkerProfile.VerificationStatus.VERIFIED,
                "bank_verified": True,
                "bank_account_masked": "****4521",
                "is_available": True,
                "available_from": "07:00",
                "available_to": "18:00",
                "city": "Cape Town",
                "lat": -33.9249,
                "lng": 18.4241,
                "hourly_rate_min_cents": 35000,
            },
        )
        if profile.verification_status != WorkerProfile.VerificationStatus.VERIFIED:
            profile.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            profile.bank_verified = True
            profile.is_available = True
            profile.save()

        admin, _ = User.objects.get_or_create(
            email="admin@ispan.test",
            defaults={
                "phone": "+27820000099",
                "role": "ADMIN",
                "active_profile": User.ActiveProfile.CUSTOMER,
                "is_customer": True,
                "is_support": True,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "iSpan",
                "email_verified": True,
                "phone_verified": True,
            },
        )
        admin.set_password("password123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_support = True
        admin.save()

        electrician = ServiceCategory.objects.get(slug="electrician")
        WorkerService.objects.update_or_create(
            worker=profile,
            category=electrician,
            defaults={"price_cents": 40000, "description": "Fault finding, DB boards, plug points"},
        )

        self.stdout.write(self.style.SUCCESS("Seeded categories + demo users"))
        self.stdout.write("  customer@ispan.test / password123")
        self.stdout.write("  worker@ispan.test / password123")
        self.stdout.write("  admin@ispan.test / password123 (verification queue)")
