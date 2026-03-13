from django.contrib import admin
from .models import User, AdditionalEmail, CapabilityProfile
# Register your models here.

admin.site.register(User)
admin.site.register(AdditionalEmail)
admin.site.register(CapabilityProfile)
#makes shown is django admin
