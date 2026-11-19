from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import WorkerProfile
from apps.catalog.models import ServiceCategory, WorkerService
from apps.customers.models import CustomerProfile
from apps.scheduling.models import MatchingConfig
from apps.safety.models import EmergencyContact
from apps.workers.models import Certificate

User = get_user_model()

# Cape Town category tree. Restricted electrical children need verified certificates.
TREE = [
    {
        "slug": "electrical",
        "name": "Electrical",
        "description": "Faults, installations, and compliance work",
        "min_cents": 25000,
        "max_cents": 90000,
        "children": [
            {
                "slug": "electrical-faults",
                "name": "Fault finding",
                "description": "Tripping, dead circuits, DB issues",
                "min_cents": 25000,
                "max_cents": 70000,
                "certs": [],
            },
            {
                "slug": "electrical-coc",
                "name": "CoC / installation",
                "description": "Certificate of Compliance and new installations (restricted)",
                "min_cents": 40000,
                "max_cents": 120000,
                "certs": ["wireman_licence", "electrical_coc_authority"],
            },
        ],
    },
    {
        "slug": "plumbing",
        "name": "Plumbing",
        "description": "Leaks, geysers, drainage",
        "min_cents": 30000,
        "max_cents": 90000,
        "children": [
            {
                "slug": "plumbing-leaks",
                "name": "Leaks & blockages",
                "description": "Urgent leak and drain work",
                "min_cents": 30000,
                "max_cents": 70000,
                "certs": [],
            },
            {
                "slug": "plumbing-geyser",
                "name": "Geyser",
                "description": "Geyser repair and replacement",
                "min_cents": 45000,
                "max_cents": 150000,
                "certs": ["pirb"],
            },
        ],
    },
    {
        "slug": "cleaning",
        "name": "Cleaning",
        "description": "Home and office cleaning",
        "min_cents": 15000,
        "max_cents": 45000,
        "children": [
            {
                "slug": "cleaning-home",
                "name": "Home cleaning",
                "description": "Standard domestic clean",
                "min_cents": 15000,
                "max_cents": 40000,
                "certs": [],
            },
        ],
    },
    {
        "slug": "gardening",
        "name": "Gardening",
        "description": "Lawn, pruning, garden care",
        "min_cents": 18000,
        "max_cents": 50000,
        "children": [],
    },
    {
        "slug": "handyman",
        "name": "Handyman",
        "description": "General repairs and odd jobs",
        "min_cents": 20000,
        "max_cents": 60000,
        "children": [],
    },
]


def upsert_category(item, parent=None, sort=100):
    cat, _ = ServiceCategory.objects.update_or_create(
        slug=item["slug"],
        defaults={
            "name": item["name"],
            "description": item.get("description", ""),
            "parent": parent,
            "suggested_min_cents": item["min_cents"],
            "suggested_max_cents": item["max_cents"],
            "min_certificate_types": item.get("certs", []),
            "commission_bps": 1250,
            "cancel_fee_bps": 5000,
            "cancel_window_minutes": 120,
            "is_active": True,
            "sort_order": sort,
        },
    )
    return cat


class Command(BaseCommand):
    help = "Seed Cape Town categories, matching config, and demo accounts"

    def handle(self, *args, **options):
        MatchingConfig.objects.get_or_create(
            name="default",
            defaults={
                "initial_radius_km": 5,
                "widen_step_km": 3,
                "widen_interval_seconds": 30,
                "max_radius_km": 25,
                "offer_seconds": 20,
                "max_concurrent_offers": 8,
            },
        )

        for i, top in enumerate(TREE):
            parent = upsert_category(top, sort=(i + 1) * 10)
            for j, child in enumerate(top.get("children") or []):
                upsert_category(child, parent=parent, sort=(i + 1) * 10 + j + 1)

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
        EmergencyContact.objects.get_or_create(
            user=customer,
            phone="+27821111999",
            defaults={"name": "Thandi's sister", "relationship": "family", "is_primary": True},
        )

        def make_worker(email, phone, first, last, lat, lng, *, certs=None, categories=None, women=False):
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "phone": phone,
                    "role": User.ActiveProfile.WORKER,
                    "active_profile": User.ActiveProfile.WORKER,
                    "is_customer": True,
                    "is_worker": True,
                    "first_name": first,
                    "last_name": last,
                    "email_verified": True,
                    "phone_verified": True,
                },
            )
            user.set_password("password123")
            user.is_worker = True
            user.is_customer = True
            user.save()
            CustomerProfile.objects.get_or_create(user=user)
            profile, _ = WorkerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "display_name": f"{first} {last}",
                    "bio": f"{first} — Cape Town trades.",
                    "verification_status": WorkerProfile.VerificationStatus.VERIFIED,
                    "bank_verified": True,
                    "bank_account_masked": "****4521",
                    "is_available": True,
                    "available_from": "07:00",
                    "available_to": "18:00",
                    "city": "Cape Town",
                    "lat": lat,
                    "lng": lng,
                    "service_radius_km": 20,
                    "hourly_rate_min_cents": 25000,
                    "women_preferred_opt_in": women,
                },
            )
            profile.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            profile.bank_verified = True
            profile.is_available = True
            profile.lat = lat
            profile.lng = lng
            profile.women_preferred_opt_in = women
            profile.save()
            for cert in certs or []:
                Certificate.objects.update_or_create(
                    worker=profile,
                    cert_type=cert,
                    defaults={"verified": True, "issuer": "Seed", "number": "SEED-1"},
                )
            for slug in categories or []:
                cat = ServiceCategory.objects.get(slug=slug)
                WorkerService.objects.update_or_create(
                    worker=profile,
                    category=cat,
                    defaults={"price_cents": cat.suggested_min_cents, "is_active": True},
                )
            EmergencyContact.objects.get_or_create(
                user=user,
                phone=f"+2782999{phone[-4:]}",
                defaults={"name": f"{first}'s emergency", "relationship": "family", "is_primary": True},
            )
            return user, profile

        # Verified electrician with CoC certs near CBD
        make_worker(
            "worker@ispan.test",
            "+27820000002",
            "Sipho",
            "Ndlovu",
            -33.9249,
            18.4241,
            certs=["wireman_licence", "electrical_coc_authority"],
            categories=["electrical", "electrical-faults", "electrical-coc", "handyman"],
        )
        # Cleaner nearby (Gardens)
        make_worker(
            "cleaner@ispan.test",
            "+27820000003",
            "Naledi",
            "Botha",
            -33.9300,
            18.4100,
            categories=["cleaning", "cleaning-home"],
            women=True,
        )
        # Second cleaner for race tests (Sea Point-ish)
        make_worker(
            "cleaner2@ispan.test",
            "+27820000004",
            "Aisha",
            "Jacobs",
            -33.9180,
            18.3900,
            categories=["cleaning", "cleaning-home"],
        )
        # Plumber without PIRB — cannot take geyser restricted jobs
        make_worker(
            "plumber@ispan.test",
            "+27820000005",
            "Johan",
            "van Wyk",
            -33.9305,
            18.4200,
            categories=["plumbing", "plumbing-leaks"],
        )
        # Plumber with PIRB
        make_worker(
            "plumber_certified@ispan.test",
            "+27820000006",
            "Fatima",
            "Hassan",
            -33.9290,
            18.4180,
            certs=["pirb"],
            categories=["plumbing", "plumbing-leaks", "plumbing-geyser"],
        )

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

        self.stdout.write(self.style.SUCCESS("Seeded categories + demo users"))
        self.stdout.write("  customer@ispan.test / password123")
        self.stdout.write("  worker@ispan.test / password123 (electrician + CoC)")
        self.stdout.write("  cleaner@ispan.test / password123")
        self.stdout.write("  cleaner2@ispan.test / password123")
        self.stdout.write("  plumber@ispan.test / password123 (no PIRB)")
        self.stdout.write("  plumber_certified@ispan.test / password123")
        self.stdout.write("  admin@ispan.test / password123")
