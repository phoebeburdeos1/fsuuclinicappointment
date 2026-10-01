from django.db import models
from django.utils import timezone

from accounts.models import User


class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'


class Doctor(models.Model):
    class Sex(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    name = models.CharField(max_length=120)
    specialty = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    sex = models.CharField(max_length=20, choices=Sex.choices, default=Sex.MALE)
    photo = models.ImageField(upload_to='doctor_photos/', blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.specialty}'

    def is_publicly_visible(self, current_date=None, current_time=None):
        if self.is_archived:
            return False

        current_date = current_date or timezone.now().date()
        current_time = current_time or timezone.now().time()
        schedules_today = self.schedules.filter(day_of_week=current_date.weekday())
        if not schedules_today.exists():
            return True
        return any(schedule.end_time > current_time for schedule in schedules_today)

    def has_live_schedule_for_date(self, target_date=None):
        target_date = target_date or timezone.now().date()
        schedules = self.schedules.filter(day_of_week=target_date.weekday())
        if not schedules.exists():
            return False
        now = timezone.now().time()
        if target_date == timezone.now().date():
            return any(schedule.end_time > now for schedule in schedules)
        return True


class DoctorSchedule(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='schedules', on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'day_of_week', 'start_time', 'end_time'], name='unique_doctor_schedule')
        ]

    def __str__(self):
        return f'{self.doctor} on {self.get_day_of_week_display()}'


class BlockedSlot(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='blocked_slots', on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, default='Blocked')

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'{self.doctor} blocked on {self.date}'


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CHECKED_IN = 'CHECKED_IN', 'Checked-in'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        NO_SHOW = 'NO_SHOW', 'No-show'

    STATUS_CHOICES = Status.choices

    patient = models.ForeignKey(User, limit_choices_to={'role': 'PATIENT'}, related_name='appointments', on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, related_name='appointments', on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    medical_summary = models.TextField(blank=True, default='')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    medications_used = models.JSONField(default=list, blank=True)
    supplies_used = models.JSONField(default=list, blank=True)
    patient_archived = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time']
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'date', 'time'], name='unique_doctor_appointment_slot')
        ]

    def __str__(self):
        return f'{self.patient} -> {self.doctor} on {self.date} at {self.time}'

    def can_cancel(self, now=None):
        from datetime import datetime, timedelta

        if now is None:
            now = datetime.now()
        appointment_dt = datetime.combine(self.date, self.time)
        return now + timedelta(hours=2) < appointment_dt


class InventoryItem(models.Model):
    class Category(models.TextChoices):
        MEDICATION = 'MEDICATION', 'Medication'
        CONSUMABLES = 'CONSUMABLES', 'Consumables'
        EQUIPMENT = 'EQUIPMENT', 'Equipment'
        GENERAL_ITEMS = 'GENERAL_ITEMS', 'General Items'

    name = models.CharField(max_length=180)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.GENERAL_ITEMS)
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.quantity} in stock)'

    @property
    def stock_status(self):
        if self.quantity == 0:
            return 'Out of Stock'
        if 1 <= self.quantity <= 10:
            return 'Low Stock'
        return 'In Stock'

    @property
    def stock_badge_class(self):
        if self.quantity == 0:
            return 'bg-danger'
        if 1 <= self.quantity <= 10:
            return 'bg-warning text-dark'
        return 'bg-success'

    @property
    def is_low_stock(self):
        return self.quantity <= 10 and self.quantity > 0

    @property
    def is_out_of_stock(self):
        return self.quantity == 0
