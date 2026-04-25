from django.contrib import admin
from .models import User, AdditionalEmail, CapabilityProfile, MailboxConnection
# Register your models here.

admin.site.register(User)
admin.site.register(AdditionalEmail)
admin.site.register(CapabilityProfile)
admin.site.register(MailboxConnection)
#makes shown is django admin
