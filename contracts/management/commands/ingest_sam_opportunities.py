from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Fetch opportunities from SAM.gov and store them as Contract records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--notice-type",
            type=str,
            default=None,
            help="Optional SAM notice type filter.",
        )
        parser.add_argument(
            "--posted-from",
            type=str,
            default=None,
            help="Optional SAM posted-from date in MM/DD/YYYY format.",
        )
        parser.add_argument(
            "--posted-to",
            type=str,
            default=None,
            help="Optional SAM posted-to date in MM/DD/YYYY format.",
        )
        parser.add_argument(
            "--keyword",
            type=str,
            default=None,
            help="Optional keyword filter.",
        )
        parser.add_argument(
            "--naics-code",
            type=str,
            default=None,
            help="Optional NAICS code filter.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=25,
            help="Number of records to request from SAM.gov.",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Offset into the SAM.gov search result set.",
        )
        parser.add_argument(
            "--max-batches",
            type=int,
            default=5,
            help="Maximum number of SAM.gov result pages to scan while looking for new records.",
        )

    def handle(self, *args, **options):
        from contracts.management.services.sam_api import ingest_sam_opportunities

        try:
            results = ingest_sam_opportunities(
                notice_type=options["notice_type"],
                posted_from=options["posted_from"],
                posted_to=options["posted_to"],
                keyword=options["keyword"],
                naics_code=options["naics_code"],
                limit=options["limit"],
                offset=options["offset"],
                max_batches=options["max_batches"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        count_ingested = results.get("count_ingested", 0)
        count_created = results.get("count_created", 0)
        count_updated = results.get("count_updated", 0)
        raw_total_records = results.get("raw_total_records")

        self.stdout.write(
            self.style.SUCCESS(
                f"Ingested {count_ingested} opportunities from SAM.gov."
            )
        )
        self.stdout.write(f"Created: {count_created}")
        self.stdout.write(f"Updated: {count_updated}")

        if raw_total_records is not None:
            self.stdout.write(f"SAM total records reported: {raw_total_records}")

        for item in results.get("results", []):
            state = "created" if item.get("created") else "updated"
            agency = item.get("agency") or "Unknown agency"
            self.stdout.write(f"[{state}] #{item['id']} {item['title']} ({agency})")
