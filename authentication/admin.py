from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Supervisor, ResetPasswordCode

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email',)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email',)

class SupervisorInline(admin.StackedInline):
    model = Supervisor
    can_delete = False
    verbose_name_plural = 'Supervisor Profile'

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    inlines = (SupervisorInline, )
    
    list_display = ('email', 'first_name', 'last_name', 'governorate', 'city', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'governorate', 'city')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone', 'governorate', 'city')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name', 'governorate', 'city', 'phone', 'is_active', 'is_staff'),
        }),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Supervisor)
admin.site.register(ResetPasswordCode)