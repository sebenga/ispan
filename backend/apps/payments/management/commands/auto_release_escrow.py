from django.core.management.base import BaseCommand

from apps.payments.services import run_auto_releases


class Command(BaseCommand):
    help = "Release held escrow after the configured auto-release window"

    def handle(self, *args, **options):
        count = run_auto_releases()
        self.stdout.write(self.style.SUCCESS(f"Auto-released {count} payment(s)"))
