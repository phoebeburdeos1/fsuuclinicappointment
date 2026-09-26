from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    PATIENT = 'PATIENT', 'Patient'


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.PATIENT)
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    photo = models.ImageField(upload_to='user_photos/', blank=True, null=True)

    def __str__(self):
        return f'{self.username} ({self.role})'


class Message(models.Model):
    sender = models.ForeignKey('User', related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey('User', related_name='received_messages', on_delete=models.CASCADE)
    subject = models.CharField(max_length=200, blank=True, default='')
    body = models.TextField()
    appointment = models.ForeignKey('admin_dashboard.Appointment', null=True, blank=True, related_name='messages', on_delete=models.SET_NULL)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} -> {self.recipient}: {self.subject or "Message"}'
