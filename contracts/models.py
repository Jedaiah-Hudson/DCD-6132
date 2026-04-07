from django.db import models
from django.conf import settings

class Contract(models.Model):

    source = models.CharField(max_length=255)
    source_mailbox = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    summary = models.TextField()
    deadline = models.DateField()
    agency = models.CharField(max_length=255)
    sub_agency = models.CharField(max_length=255, blank=True)
    naics_code = models.CharField(max_length=50, blank=True)
    hyperlink = models.URLField(blank=True)
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