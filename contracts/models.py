from django.db import models
from django.conf import settings

class Contract(models.Model):

    class SourceType(models.TextChoices):
        GMAIL = "gmail", "Gmail"
        OUTLOOK = "outlook", "Outlook"
        PROCUREMENT = "procurement", "Procurement"
    
    source = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        db_index=True
    )
    procurement_portal = models.CharField(max_length=50, blank=True, db_index=True)

    title = models.CharField(max_length=255)
    summary = models.TextField()
    deadline = models.DateTimeField(null=True, blank=True)
    agency = models.CharField(max_length=255)
    sub_agency = models.CharField(max_length=255, blank=True)
    naics_code = models.CharField(max_length=50, blank=True)
    hyperlink = models.URLField(blank=True, db_index=True)
    partner_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title

    # def save(self, *args, **kwargs):
    #     if self.naics_code:
    #         self.category = get_category_for_naics(self.naics_code)
    #     super().save(*args, **kwargs)

class UserContractProgress(models.Model):

    class ProgressChoices(models.TextChoices):
        NONE = "NONE", "None"
        PENDING = "PENDING", "Pending"
        WON = "WON", "Won"
        LOST = "LOST", "Lost"

    class WorkflowChoices(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        REVIEWING = "REVIEWING", "Reviewing"
        DRAFTING = "DRAFTING", "Drafting"
        SUBMITTED = "SUBMITTED", "Submitted"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contract_progress_labels"
    )

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="user_progress"
    )

    contract_progress = models.CharField(
        max_length=10,
        choices=ProgressChoices.choices,
        default=ProgressChoices.NONE
    )

    workflow_status = models.CharField(
        max_length=20,
        choices=WorkflowChoices.choices,
        default="NOT_STARTED"
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "contract")

    def __str__(self):
        return f"{self.user} - {self.contract.title} - {self.contract_progress}"


class ContractNotification(models.Model):

    class NotificationType(models.TextChoices):
        DEADLINE = "DEADLINE", "Deadline"
        STATUS = "STATUS", "Status"
        PROGRESS = "PROGRESS", "Progress"
        WORKFLOW = "WORKFLOW", "Workflow"

    class SeverityChoices(models.TextChoices):
        INFO = "INFO", "Info"
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contract_notifications"
    )

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="contract_notifications"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    severity = models.CharField(
        max_length=10,
        choices=SeverityChoices.choices,
        default=SeverityChoices.INFO,
    )
    unique_key = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    message = models.TextField()
    due_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "unique_key")
        ordering = ("is_read", "-created_at")

    def __str__(self):
        return f"{self.user} - {self.title}"


class EmailIngestionMessage(models.Model):
    mailbox_connection = models.ForeignKey(
        "accounts.MailboxConnection",
        on_delete=models.CASCADE,
        related_name="ingested_messages",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        related_name="email_ingestion_messages",
        null=True,
        blank=True,
    )
    external_message_id = models.CharField(max_length=255)
    source_email = models.EmailField(blank=True)
    sender = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    was_candidate = models.BooleanField(default=False)
    filter_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("mailbox_connection", "external_message_id")
        ordering = ("-received_at", "-created_at")

    def __str__(self):
        return f"{self.mailbox_connection.mailbox_email} - {self.external_message_id}"

class ContractNote(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="notes"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contract_notes"
    )

    title = models.CharField(max_length=255, blank=True)
    body = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title if self.title else f"Note for {self.contract.title}"
    
class NAICSCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=255)
    broad_category = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.code} - {self.title}"
