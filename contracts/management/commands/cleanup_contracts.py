import re
import html

from django.core.management.base import BaseCommand
from contracts.models import Contract


class Command(BaseCommand):
    help = "Cleans HTML from Contract.summary and truncates it"

    def handle(self, *args, **kwargs):
        contracts = Contract.objects.exclude(summary__isnull=True).exclude(summary="")

        count = 0

        for contract in contracts.iterator():
            cleaned = html.unescape(contract.summary or "")
            cleaned = re.sub(r"<[^>]+>", "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()

            if cleaned != contract.summary:
                contract.summary = cleaned
                contract.save(update_fields=["summary"])
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {count} contracts"))