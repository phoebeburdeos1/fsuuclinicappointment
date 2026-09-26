from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from accounts.models import User, UserRole
from accounts.utils import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, ensure_default_admin
from admin_dashboard.models import Appointment, BlockedSlot, DayOfWeek, Doctor, DoctorSchedule


class Command(BaseCommand):
    help = 'Seed demo data for the clinic appointment system.'

    def handle(self, *args, **options):
        ensure_default_admin()
        User.objects.filter(username='admin').delete()

        patient1, _ = User.objects.get_or_create(username='patient1', defaults={'email': 'patient1@clinicflow.test', 'role': UserRole.PATIENT, 'phone': '5551112222'})
        patient1.set_password('PatientPass123')
        patient1.save()

        patient2, _ = User.objects.get_or_create(username='patient2', defaults={'email': 'patient2@clinicflow.test', 'role': UserRole.PATIENT, 'phone': '5552223333'})
        patient2.set_password('PatientPass123')
        patient2.save()

        doctor_one, _ = Doctor.objects.get_or_create(name='Dr. James Lee', defaults={'specialty': 'Cardiology', 'bio': 'Cardiology specialist helping patients manage long-term heart health.'})
        doctor_two, _ = Doctor.objects.get_or_create(name='Dr. Aisha Khan', defaults={'specialty': 'Dermatology', 'bio': 'Dermatologist focused on skin health and allergy care.'})
        doctor_three, _ = Doctor.objects.get_or_create(name='Dr. Rebecca Ortiz', defaults={'specialty': 'Family Medicine', 'bio': 'General care physician for adults and families.'})

        schedule_data = [
            (doctor_one, DayOfWeek.MONDAY, time(9, 0), time(17, 0), 30),
            (doctor_one, DayOfWeek.WEDNESDAY, time(9, 0), time(17, 0), 30),
            (doctor_one, DayOfWeek.FRIDAY, time(9, 0), time(17, 0), 30),
            (doctor_two, DayOfWeek.TUESDAY, time(10, 0), time(16, 0), 30),
            (doctor_two, DayOfWeek.THURSDAY, time(10, 0), time(16, 0), 30),
            (doctor_three, DayOfWeek.MONDAY, time(8, 0), time(14, 0), 30),
            (doctor_three, DayOfWeek.TUESDAY, time(8, 0), time(14, 0), 30),
            (doctor_three, DayOfWeek.WEDNESDAY, time(8, 0), time(14, 0), 30),
        ]

        for doctor, day, start, end, duration in schedule_data:
            DoctorSchedule.objects.get_or_create(doctor=doctor, day_of_week=day, defaults={'start_time': start, 'end_time': end, 'slot_duration': duration})

        today = date.today()
        BlockedSlot.objects.get_or_create(
            doctor=doctor_one,
            date=today + timedelta(days=2),
            defaults={'start_time': time(12, 0), 'end_time': time(13, 0), 'reason': 'Lunch break'},
        )

        Appointment.objects.get_or_create(
            patient=patient1,
            doctor=doctor_one,
            date=today + timedelta(days=1),
            time=time(10, 30),
            defaults={'status': Appointment.Status.CONFIRMED, 'notes': 'Cardiology follow-up'},
        )
        Appointment.objects.get_or_create(
            patient=patient2,
            doctor=doctor_two,
            date=today + timedelta(days=3),
            time=time(11, 0),
            defaults={'status': Appointment.Status.PENDING, 'notes': 'Skin consultation'},
        )
        Appointment.objects.get_or_create(
            patient=patient1,
            doctor=doctor_three,
            date=today + timedelta(days=2),
            time=time(9, 30),
            defaults={'status': Appointment.Status.CHECKED_IN, 'notes': 'Annual checkup'},
        )

        self.stdout.write(self.style.SUCCESS('Demo clinic data created successfully.'))
