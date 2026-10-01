from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Message, User


class RoleLoginRedirectTests(TestCase):
    def test_root_renders_landing_page_for_anonymous_users(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')

    def test_default_admin_redirects_to_admin_dashboard(self):
        admin, _ = User.objects.get_or_create(
            username='admin2',
            defaults={
                'email': 'admin2@fsuu.edu.ph',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin.set_password('password1234')
        admin.save()
        self.client.force_login(admin)
        response = self.client.get(reverse('landing_page'))
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_default_admin_can_log_in_with_email(self):
        admin, _ = User.objects.get_or_create(
            username='admin2',
            defaults={
                'email': 'admin2@fsuu.edu.ph',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin.set_password('password1234')
        admin.save()

        response = self.client.post(
            reverse('login'),
            {'username': 'admin2@fsuu.edu.ph', 'password': 'password1234'},
            follow=True,
        )

        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_patient_views_landing_page(self):
        patient = User.objects.create_user(username='patient', email='patient@example.com', password='StrongPass123', role='PATIENT')
        self.client.force_login(patient)
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')

    def test_authenticated_users_do_not_see_repeated_header_actions(self):
        patient = User.objects.create_user(username='patient_hdr', email='patient_hdr@example.com', password='StrongPass123', role='PATIENT')
        self.client.force_login(patient)
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '>Messages</a>')
        self.assertNotContains(response, 'My Dashboard')
        self.assertNotContains(response, 'Logout')

    def test_protected_patient_dashboard_redirects_to_project_login(self):
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/?next=/dashboard/', fetch_redirect_response=False)

    def test_login_page_has_clean_header_and_login_form_features(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back! Please enter your credentials to access your account.')
        self.assertContains(response, 'Remember me')
        self.assertContains(response, 'Forgot password?')
        self.assertContains(response, 'Register here')
        self.assertNotContains(response, 'Book Appointment')
        self.assertNotContains(response, 'Log In')

    def test_admin_and_patient_can_send_messages(self):
        admin = User.objects.create_user(
            username='admin_msg',
            email='admin_msg@fsuu.edu.ph',
            password='password1234',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        patient = User.objects.create_user(
            username='patient_msg',
            email='patient_msg@example.com',
            password='StrongPass123',
            role='PATIENT',
        )

        self.client.force_login(admin)
        response = self.client.post(
            reverse('send_message'),
            {'recipient': patient.id, 'subject': 'Appointment question', 'body': 'Can we discuss the checkup?'}
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(patient.received_messages.filter(sender=admin).exists())
        self.assertEqual(patient.received_messages.count(), 1)

    def test_notification_payload_returns_unread_badge_counts(self):
        patient = User.objects.create_user(
            username='patient_badges',
            email='patient_badges@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        admin = User.objects.create_user(
            username='admin_badges',
            email='admin_badges@example.com',
            password='StrongPass123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        Message.objects.create(sender=patient, recipient=admin, subject='Question', body='One unread message')

        self.client.force_login(admin)
        response = self.client.get(reverse('notification_payload'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['message_count'], 1)

    def test_messages_page_has_dashboard_sidebar_and_search_input(self):
        patient = User.objects.create_user(
            username='patient_msg_ui',
            email='patient_msg_ui@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        admin = User.objects.create_user(
            username='admin_msg_ui',
            email='admin_msg_ui@fsuu.edu.ph',
            password='password1234',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )

        self.client.force_login(patient)
        response = self.client.get(reverse('messages_page') + '?recipient=' + str(admin.id))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Home')
        self.assertContains(response, 'Search conversation...')
        self.assertContains(response, 'View profile')

    def test_user_profile_page_renders_uploaded_photo(self):
        patient = User.objects.create_user(
            username='profile_user',
            email='profile_user@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        patient.photo = SimpleUploadedFile('avatar.png', b'fake-image-content', content_type='image/png')
        patient.save()

        self.client.force_login(patient)
        response = self.client.get(reverse('user_profile', args=[patient.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profile_user')
        self.assertContains(response, '/media/user_photos/')
        self.assertIn(patient.photo.url, response.content.decode())
        self.assertTrue(patient.photo.name)
        self.assertTrue(patient.photo.storage.exists(patient.photo.name))

    def test_admin_patient_profile_inherits_dashboard_shell_and_has_back_actions(self):
        admin = User.objects.create_user(
            username='admin_profile_shell',
            email='admin_profile_shell@fsuu.edu.ph',
            password='password1234',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        patient = User.objects.create_user(
            username='patient_profile_shell',
            email='patient_profile_shell@example.com',
            password='StrongPass123',
            role='PATIENT',
        )

        self.client.force_login(admin)
        response = self.client.get(reverse('admin_patient_profile', args=[patient.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'history.back()')
        self.assertNotContains(response, 'Send Message')
        self.assertContains(response, 'Dashboard Home')
        self.assertContains(response, 'patient-profile-shell')

    def test_staff_and_admin_can_access_staff_dashboard(self):
        staff = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            password='StrongPass123',
            role='STAFF',
            is_staff=True,
        )
        admin = User.objects.create_user(
            username='admin_staff',
            email='admin_staff@fsuu.edu.ph',
            password='StrongPass123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )

        self.client.force_login(staff)
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Today\'s Patient Queue')

        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Appointment timeline')

        self.client.force_login(admin)
        response = self.client.get(reverse('inventory'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory Overview')

    def test_patient_is_blocked_from_staff_dashboard_and_inventory(self):
        patient = User.objects.create_user(
            username='blocked_patient',
            email='blocked_patient@example.com',
            password='StrongPass123',
            role='PATIENT',
        )
        self.client.force_login(patient)

        response = self.client.get(reverse('staff_dashboard'), follow=True)
        self.assertRedirects(response, reverse('patient_dashboard'))
        self.assertContains(response, 'Access Restricted: Staff and Admin only.')

        response = self.client.get(reverse('inventory'), follow=True)
        self.assertRedirects(response, reverse('patient_dashboard'))
        self.assertContains(response, 'Access Restricted: Staff and Admin only.')
