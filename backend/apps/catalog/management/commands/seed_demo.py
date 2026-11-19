from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import WorkerProfile
from apps.catalog.models import ServiceCategory, WorkerService

User = get_user_model()

CATEGORIES = [
    ("electrician", "Electrician", "Wiring, faults, installations", 25000, 80000),
    ("plumber", "Plumber", "Leaks, geysers, drainage", 30000, 90000),
    ("cleaner", "Cleaner", "Home and office cleaning", 15000, 45000),
    ("gardener", "Gardener", "Lawn, pruning, garden care", 18000, 50000),
    ("handyman", "Handyman", "General repairs and odd jobs", 20000, 60000),
]


class Command(BaseCommand):
    help = "Seed service categories and demo customer/worker accounts"

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
                "role": User.Role.CUSTOMER,
                "first_name": "Thandi",
                "last_name": "Molefe",
                "email_verified": True,
                "phone_verified": True,
            },
        )
        customer.set_password("password123")
        customer.save()

        worker, _ = User.objects.get_or_create(
            email="worker@ispan.test",
            defaults={
                "phone": "+27820000002",
                "role": User.Role.WORKER,
                "first_name": "Sipho",
                "last_name": "Ndlovu",
                "email_verified": True,
                "phone_verified": True,
            },
        )
        worker.set_password("password123")
        worker.save()

        profile, _ = WorkerProfile.objects.get_or_create(
            user=worker,
            defaults={
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
            profile.is_available = True
            profile.save()

        electrician = ServiceCategory.objects.get(slug="electrician")
        WorkerService.objects.update_or_create(
            worker=profile,
            category=electrician,
            defaults={"price_cents": 40000, "description": "Fault finding, DB boards, plug points"},
        )

        self.stdout.write(self.style.SUCCESS("Seeded categories + demo users"))
        self.stdout.write("  customer@ispan.test / password123")
        self.stdout.write("  worker@ispan.test / password123")
