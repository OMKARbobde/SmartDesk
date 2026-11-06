from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):

    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('AGENT', 'Support Agent'),
        ('EMPLOYEE', 'Employee'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='EMPLOYEE'
    )

    def __str__(self):
        return f"{self.username} - {self.role}"


class EmployeeProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True
    )

    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.PROTECT,
        related_name='employees'
    )

    designation = models.CharField(max_length=100)

    phone_number = models.CharField(
        max_length=15,
        blank=True
    )

    is_available = models.BooleanField(default=True)

    joined_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.employee_id}"