from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0010_usercontractprogress_notes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContractNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("DEADLINE", "Deadline"), ("STATUS", "Status"), ("PROGRESS", "Progress"), ("WORKFLOW", "Workflow")], max_length=20)),
                ("severity", models.CharField(choices=[("INFO", "Info"), ("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")], default="INFO", max_length=10)),
                ("unique_key", models.CharField(max_length=255)),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contract_notifications", to="contracts.contract")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contract_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ("is_read", "-created_at"),
                "unique_together": {("user", "unique_key")},
            },
        ),
    ]
