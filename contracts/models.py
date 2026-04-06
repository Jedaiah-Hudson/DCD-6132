from django.db import models


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

    def __str__(self):
        return self.title
    
    