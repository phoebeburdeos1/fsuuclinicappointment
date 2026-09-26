from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from admin_dashboard.models import Appointment, Doctor, DoctorSchedule


class PatientDashboardLayoutTests(TestCase):
    def test_patient_dashboard_home_has_dashboard_sections(self):
        patient = User.objects.create_user(
            username='patient1',
            email='patient1@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Smith', specialty='Cardiology', bio='Heart care specialist')
        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date.today() + timedelta(days=1),
            time=time(9, 0),
            status=Appointment.Status.CONFIRMED,
        )

        self.client.force_login(patient)
        response = self.client.get(reverse('patient_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hello, patient1!')
        self.assertContains(response, 'Upcoming appointment')
        self.assertContains(response, 'Find a Doctor')
        self.assertContains(response, 'My Appointments')

    def test_patient_can_book_an_available_slot(self):
        patient = User.objects.create_user(
            username='patient_booking',
            email='patient_booking@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Thompson', specialty='Dermatology', bio='Skin specialist')
        appointment_date = date.today() + timedelta(days=2)
        slot_time = time(10, 0)
        DoctorSchedule.objects.create(
            doctor=doctor,
            day_of_week=appointment_date.weekday(),
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration=30,
        )

        self.client.force_login(patient)
        response = self.client.post(
            reverse('book_appointment'),
            {'doctor': doctor.id, 'date': appointment_date.isoformat(), 'time': slot_time.strftime('%H:%M'), 'notes': 'Need a consultation'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Appointment.objects.filter(patient=patient, doctor=doctor, date=appointment_date).exists())

    def test_slot_availability_endpoint_returns_times(self):
        patient = User.objects.create_user(
            username='patient_slots',
            email='patient_slots@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Ramos', specialty='General Medicine', bio='General care doctor')
        appointment_date = date.today() + timedelta(days=1)
        DoctorSchedule.objects.create(
            doctor=doctor,
            day_of_week=appointment_date.weekday(),
            start_time=time(9, 0),
            end_time=time(11, 30),
            slot_duration=30,
        )

        self.client.force_login(patient)
        response = self.client.get(reverse('doctor_slots'), {'doctor_id': doctor.id, 'date': appointment_date.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['has_slots'])
        self.assertIn('09:00', response.json()['slots'])

    def test_archived_doctors_are_hidden_from_public_directory(self):
        patient = User.objects.create_user(
            username='patient_archived',
            email='patient_archived@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(
            name='Dr. Archived',
            specialty='Neurology',
            bio='Former active doctor',
            is_archived=True,
        )
        DoctorSchedule.objects.create(
            doctor=doctor,
            day_of_week=date.today().weekday(),
            start_time=time(8, 0),
            end_time=time(16, 0),
            slot_duration=30,
        )

        self.client.force_login(patient)
        response = self.client.get(reverse('patient_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Dr. Archived')

    def test_doctor_gender_can_be_saved(self):
        doctor = Doctor.objects.create(
            name='Dr. Rivera',
            specialty='Pediatrics',
            sex=Doctor.Sex.FEMALE,
        )

        self.assertEqual(doctor.sex, Doctor.Sex.FEMALE)

    def test_patient_dashboard_shows_empty_state_and_quick_actions(self):
        patient = User.objects.create_user(
            username='patient_qc',
            email='patient_qc@example.com',
            password='StrongPass123',
            role='PATIENT',
        )

        self.client.force_login(patient)
        response = self.client.get(reverse('patient_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No upcoming visits scheduled. Need to see a specialist?')
        self.assertContains(response, 'Book a Consultation')
        self.assertContains(response, 'Manage Profile')
        self.assertContains(response, 'bi bi-search')
