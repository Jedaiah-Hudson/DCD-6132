# Generated manually for frontend contract relationship labels

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0012_emailingestionmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="usercontractprogress",
            name="relationship_label",
            field=models.CharField(
                choices=[
                    ("UNASSIGNED", "Unassigned"),
                    ("PRIME", "Prime"),
                    ("SUBCONTRACTOR", "Sub"),
                    ("TEAMING", "Teaming"),
                    ("VENDOR", "Vendor"),
                    ("CONSULTANT", "Consultant"),
                ],
                default="UNASSIGNED",
                max_length=20,
            ),
        ),
    ]
