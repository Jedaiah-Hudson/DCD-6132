from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand

from contracts.models import NAICSCode


def normalize_naics_code(code):
    if not code:
        return ""

    code = str(code).strip()

    if code.endswith(".0"):
        code = code[:-2]

    return code


def categorize_naics_by_code(code):
    code = normalize_naics_code(code)

    if not code:
        return ""

    exact_map = {
        "513210": "software",
        "518210": "cloud_data_web",
        "519290": "information_services",
        "541511": "software",
        "541512": "it_services",
        "541513": "it_services",
        "541519": "it_services",
        "541330": "engineering",
        "541611": "management_consulting",
        "541612": "management_consulting",
        "541613": "management_consulting",
        "541614": "management_consulting",
        "541618": "management_consulting",
        "611420": "education_training",
        "621111": "healthcare",
        "621511": "healthcare",
        "622110": "healthcare",
        "488510": "logistics",
        "493110": "logistics",
        "236220": "construction",
        "237110": "construction",
        "237120": "construction",
        "237130": "construction",
        "334111": "computer_hardware",
        "334112": "computer_hardware",
        "334118": "computer_hardware",
        "334210": "communications_equipment",
        "334220": "communications_equipment",
        "334290": "communications_equipment",
        "334413": "electronics_semiconductors",
        "334418": "electronics_semiconductors",
        "336411": "aerospace",
        "336412": "aerospace",
        "336413": "aerospace",
        "336414": "aerospace",
        "336415": "aerospace",
        "336419": "aerospace",
        "339112": "medical_manufacturing",
        "339113": "medical_manufacturing",
        "339114": "medical_manufacturing",
        "339115": "medical_manufacturing",
        "423430": "technology_wholesale",
        "423450": "healthcare_wholesale",
    }

    if code in exact_map:
        return exact_map[code]

    if code.startswith("3341"):
        return "computer_hardware"
    if code.startswith(("3342", "3343")):
        return "communications_equipment"
    if code.startswith(("3344", "3345", "3346")):
        return "electronics_instruments"
    if code.startswith("3254"):
        return "pharmaceuticals"
    if code.startswith("3391"):
        return "medical_equipment"
    if code.startswith("3364"):
        return "aerospace"
    if code.startswith("5413"):
        return "engineering_architecture"
    if code.startswith("5415"):
        return "software_it"
    if code.startswith("5416"):
        return "consulting"
    if code.startswith("5417"):
        return "research_development"
    if code.startswith("517"):
        return "telecommunications"
    if code.startswith("518"):
        return "cloud_data_web"
    if code.startswith(("513", "516", "519")):
        return "information_services"
    if code.startswith("42343"):
        return "technology_wholesale"
    if code.startswith("42345"):
        return "healthcare_wholesale"
    if code.startswith(("42381", "42383")):
        return "industrial_equipment"

    if code.startswith("11"):
        return "agriculture"
    if code.startswith("21"):
        return "mining_energy"
    if code.startswith("22"):
        return "utilities"
    if code.startswith("23"):
        return "construction"
    if code.startswith(("31", "32", "33")):
        return "manufacturing"
    if code.startswith("42"):
        return "wholesale"
    if code.startswith(("44", "45")):
        return "retail"
    if code.startswith(("48", "49")):
        return "transportation_logistics"
    if code.startswith("51"):
        return "information"
    if code.startswith("52"):
        return "finance_insurance"
    if code.startswith("53"):
        return "real_estate_rental"
    if code.startswith("54"):
        return "professional_services"
    if code.startswith("55"):
        return "management"
    if code.startswith("56"):
        return "administrative_support"
    if code.startswith("61"):
        return "education"
    if code.startswith("62"):
        return "healthcare_social_assistance"
    if code.startswith("71"):
        return "arts_entertainment_recreation"
    if code.startswith("72"):
        return "accommodation_food_services"
    if code.startswith("81"):
        return "other_services"
    if code.startswith("92"):
        return "public_administration"

    return "other"


class Command(BaseCommand):
    help = "Load NAICS codes from the 2022 Census NAICS structure workbook"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to the NAICS xlsx file",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        df = pd.read_excel(file_path, header=2)

        possible_code_cols = ["2022 NAICS Code", "Code", "NAICS Code"]
        possible_title_cols = ["2022 NAICS Title", "Title", "NAICS Title"]

        code_col = next((c for c in possible_code_cols if c in df.columns), None)
        title_col = next((c for c in possible_title_cols if c in df.columns), None)

        if not code_col or not title_col:
            self.stderr.write(self.style.ERROR(
                f"Could not find expected columns. Found: {list(df.columns)}"
            ))
            return

        created = 0
        updated = 0

        for _, row in df.iterrows():
            code = normalize_naics_code(row[code_col])
            title = str(row[title_col]).strip()

            if not code or code.lower() == "nan":
                continue

            broad_category = categorize_naics_by_code(code)

            _, was_created = NAICSCode.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "broad_category": broad_category,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created}, updated {updated}."
        ))