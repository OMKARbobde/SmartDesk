from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, EmployeeProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    fieldsets = UserAdmin.fieldsets + (
        ('SmartDesk Information', {
            'fields': ('role',)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('SmartDesk Information', {
            'fields': ('role',)
        }),
    )


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):

    list_display = (
        'employee_id',
        'user',
        'department',
        'designation',
        'is_available',
    )

    search_fields = (
        'employee_id',
        'user__username',
        'designation',
    )

    list_filter = (
        'department',
        'is_available',
    )