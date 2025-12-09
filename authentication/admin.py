from django.contrib import admin

# Register your models here.
from .models import User , Supervisor , ResetPasswordCode

admin.site.register(User)
admin.site.register(Supervisor)
admin.site.register(ResetPasswordCode)