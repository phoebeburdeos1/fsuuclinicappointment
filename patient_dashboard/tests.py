from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from admin_dashboard.models import Appointment, BlockedSlot, Doctor, DoctorSchedule


class PatientDashboardLayoutTests(TestCase):
    def test_patient_can_archive_and_restore_own_appointment(self):
        patient = User.objects.create_user(
            username='patient_archive',
            email='patient_archive@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Archive', specialty='Family Medicine')
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date.today() + timedelta(days=1),
            time=time(9, 0),
        )
        self.client.force_login(patient)

        response = self.client.post(reverse('archive_appointment', args=[appointment.id]))
        self.assertRedirects(response, reverse('my_appointments'))
        appointment.refresh_from_db()
        self.assertTrue(appointment.patient_archived)

        response = self.client.post(reverse('restore_appointment', args=[appointment.id]))
        self.assertRedirects(response, reverse('my_appointments'))
        appointment.refresh_from_db()
        self.assertFalse(appointment.patient_archived)

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
        self.assertContains(response, 'grid-template-columns: 260px minmax(0, 1fr);')
        self.assertNotContains(response, 'margin-left: calc(50% - 50vw)')
        self.assertContains(response, '.patient-main > .tab-content')
        self.assertContains(response, 'overflow-y: auto;')

    def test_patient_profile_page_renders_dark_mode_contrast_styles(self):
        patient = User.objects.create_user(
            username='patient_profile_dark',
            email='patient_profile_dark@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        self.client.force_login(patient)

        response = self.client.get(reverse('profile_update'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile photo')
        self.assertContains(response, 'body[data-theme="dark"] .profile-field label')
        self.assertContains(response, 'body[data-theme="dark"] .profile-upload')

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
            {
                'doctor': doctor.id,
                'date': appointment_date.isoformat(),
                'time': slot_time.strftime('%H:%M'),
                'visit_type': 'Other',
                'visit_type_other': 'Medical Certificate',
                'notes': 'Need a consultation',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        appointment = Appointment.objects.get(patient=patient, doctor=doctor, date=appointment_date)
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(appointment.notes, 'Other: Medical Certificate: Need a consultation')
        self.assertNotContains(
            response,
            '/admin-dashboard/settings/ now opens System Settings as the active section instead of showing Overview above it.',
        )

    def test_other_visit_type_requires_specification(self):
        patient = User.objects.create_user(
            username='patient_other_visit',
            email='patient_other_visit@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Other', specialty='General Medicine')

        self.client.force_login(patient)
        response = self.client.post(
            reverse('book_appointment'),
            {
                'doctor': doctor.id,
                'date': (date.today() + timedelta(days=1)).isoformat(),
                'time': '10:00',
                'visit_type': 'Other',
                'notes': 'Need a consultation',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please specify your visit type.')
        self.assertFalse(Appointment.objects.filter(patient=patient, doctor=doctor).exists())

    def test_patient_booking_requires_reason_for_visit(self):
        patient = User.objects.create_user(
            username='patient_reason_required',
            email='patient_reason_required@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Reason', specialty='General Medicine', bio='General care doctor')
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
            {'doctor': doctor.id, 'date': appointment_date.isoformat(), 'time': slot_time.strftime('%H:%M'), 'notes': ''},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please provide a reason for your visit.')
        self.assertFalse(Appointment.objects.filter(patient=patient, doctor=doctor).exists())

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

    def test_full_day_block_removes_all_weekly_slots(self):
        patient = User.objects.create_user(
            username='patient_full_day_block',
            email='patient_full_day_block@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        doctor = Doctor.objects.create(name='Dr. Unavailable', specialty='Family Medicine')
        appointment_date = date.today() + timedelta(days=2)
        DoctorSchedule.objects.create(
            doctor=doctor,
            day_of_week=appointment_date.weekday(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration=30,
        )
        BlockedSlot.objects.create(
            doctor=doctor,
            date=appointment_date,
            start_time=time(0, 0),
            end_time=time(23, 59),
            reason='Holiday',
        )

        self.client.force_login(patient)
        response = self.client.get(
            reverse('doctor_slots'),
            {'doctor_id': doctor.id, 'date': appointment_date.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['has_slots'])
        self.assertEqual(response.json()['slots'], [])

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

    def test_available_today_filter_marks_unscheduled_doctor_unavailable(self):
        patient = User.objects.create_user(
            username='patient_availability',
            email='patient_availability@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        Doctor.objects.create(name='Dr. Not Scheduled Today', specialty='Cardiology')
        self.client.force_login(patient)

        response = self.client.get(reverse('patient_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-doctor-available="false"')

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
