from datetime import time

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Appointment, BlockedSlot, Doctor, DoctorSchedule, InventoryItem


class AdminSettingsTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_user(
			username='settings_admin',
			email='settings@example.com',
			password='StrongPass123',
			role='ADMIN',
			is_staff=True,
			is_superuser=True,
		)
		self.client.force_login(self.admin)

	def test_settings_route_has_three_subtabs(self):
		response = self.client.get(reverse('admin_settings'))
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['settings_page'])
		self.assertContains(response, 'id="settings-tab" class="admin-section active show tab-pane fade"')
		self.assertNotContains(response, 'id="overview-tab"')
		self.assertContains(response, 'System Settings')
		self.assertContains(response, 'Archives')
		self.assertContains(response, 'Inventory')
		self.assertContains(response, 'My Profile')
		self.assertContains(response, 'Archived Doctors')
		self.assertContains(response, 'Archived Appointments')
		self.assertContains(response, f'href="{reverse("admin_dashboard")}?tab=overview"')
		self.assertContains(response, f'href="{reverse("admin_dashboard")}?tab=appointments"')
		self.assertContains(response, f'href="{reverse("admin_dashboard")}?tab=doctors"')
		self.assertContains(response, f'href="{reverse("admin_dashboard")}?tab=schedules"')

	def test_overview_route_does_not_render_settings_content(self):
		response = self.client.get(reverse('admin_dashboard'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Appointments per doctor')
		self.assertNotContains(response, 'System Settings')
		self.assertNotContains(response, 'id="settings-tab"')

	def test_settings_inventory_add_creates_item(self):
		response = self.client.post(reverse('admin_settings'), {
			'settings_action': 'inventory_add',
			'name': 'Exam gloves',
			'category': InventoryItem.Category.CONSUMABLES,
			'quantity': '24',
			'unit_price': '2.50',
		})
		self.assertRedirects(response, reverse('admin_settings') + '?settings=inventory')
		self.assertTrue(InventoryItem.objects.filter(name='Exam gloves', quantity=24).exists())

	def test_settings_restock_increments_existing_inventory(self):
		item = InventoryItem.objects.create(
			name='Surgical masks',
			category=InventoryItem.Category.CONSUMABLES,
			quantity=8,
		)
		response = self.client.post(reverse('admin_settings'), {
			'settings_action': 'inventory_restock',
			'item_id': item.id,
			'quantity_received': '12',
		})
		self.assertRedirects(response, reverse('admin_settings') + '?settings=restock')
		item.refresh_from_db()
		self.assertEqual(item.quantity, 20)

	def test_settings_profile_updates_current_admin(self):
		response = self.client.post(reverse('admin_settings'), {
			'settings_action': 'save_profile',
			'first_name': 'Alex',
			'last_name': 'Admin',
			'email': 'alex.admin@example.com',
			'phone': '09171234567',
		})
		self.assertRedirects(response, reverse('admin_settings') + '?settings=profile')
		self.admin.refresh_from_db()
		self.assertEqual(self.admin.first_name, 'Alex')
		self.assertEqual(self.admin.email, 'alex.admin@example.com')

	def test_settings_password_update_preserves_session(self):
		response = self.client.post(reverse('admin_settings'), {
			'settings_action': 'change_password',
			'current_password': 'StrongPass123',
			'new_password': 'AnotherStrongPass123!',
			'confirm_password': 'AnotherStrongPass123!',
		})
		self.assertRedirects(response, reverse('admin_settings') + '?settings=profile')
		self.admin.refresh_from_db()
		self.assertTrue(self.admin.check_password('AnotherStrongPass123!'))

	def test_completed_appointment_row_has_summary_action_not_complete_action(self):
		patient = User.objects.create_user(
			username='completed_patient',
			email='completed_patient@example.com',
			password='StrongPass123',
			role='PATIENT',
		)
		doctor = Doctor.objects.create(name='Dr. Record', specialty='Family Medicine')
		appointment = Appointment.objects.create(
			patient=patient,
			doctor=doctor,
			date='2026-10-02',
			time='09:00',
			status=Appointment.Status.COMPLETED,
			medical_summary='Follow-up recommended.',
		)

		response = self.client.get(reverse('admin_dashboard') + '?tab=appointments')

		self.assertContains(response, 'data-appointment-status="completed"')
		self.assertContains(response, f'data-bs-target="#adminSummaryModal{appointment.id}"')
		self.assertContains(response, f'data-confirm-title="Archive Appointment Record?"')
		self.assertContains(response, 'It will be moved to the Archived Appointments list in Settings.')
		self.assertNotContains(response, f'data-bs-target="#adminConsultationModal{appointment.id}"')

	def test_admin_can_archive_and_restore_completed_appointment(self):
		patient = User.objects.create_user(
			username='archived_patient',
			email='archived_patient@example.com',
			password='StrongPass123',
			role='PATIENT',
		)
		doctor = Doctor.objects.create(name='Dr. Archive', specialty='Family Medicine')
		appointment = Appointment.objects.create(
			patient=patient,
			doctor=doctor,
			date='2026-10-02',
			time='09:30',
			status=Appointment.Status.COMPLETED,
		)

		response = self.client.post(reverse('appointment_archive', args=[appointment.id]))
		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=appointments')
		appointment.refresh_from_db()
		self.assertTrue(appointment.is_archived)

		active_timeline = self.client.get(reverse('admin_dashboard') + '?tab=appointments')
		self.assertNotContains(active_timeline, 'archived_patient')
		archive_page = self.client.get(reverse('admin_settings') + '?settings=archives&archive_tab=appointments')
		self.assertContains(archive_page, 'archived_patient')
		self.assertContains(archive_page, f'action="{reverse("appointment_restore", args=[appointment.id])}"')

		response = self.client.post(reverse('appointment_restore', args=[appointment.id]))
		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=appointments')
		appointment.refresh_from_db()
		self.assertFalse(appointment.is_archived)
		active_timeline = self.client.get(reverse('admin_dashboard') + '?tab=appointments')
		self.assertContains(active_timeline, 'archived_patient')

	def test_weekday_schedule_submission_creates_one_entry_per_day(self):
		doctor = Doctor.objects.create(name='Dr. Weekday', specialty='Family Medicine')
		response = self.client.post(reverse('admin_dashboard'), {
			'tab': 'schedules',
			'doctor': doctor.id,
			'days_of_week': ['0', '1', '2', '3', '4'],
			'start_time': '09:00',
			'end_time': '17:00',
			'slot_duration': '30',
			'save_schedule': '1',
		})

		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=schedules')
		self.assertEqual(DoctorSchedule.objects.filter(doctor=doctor).count(), 5)
		self.assertEqual(
			set(DoctorSchedule.objects.filter(doctor=doctor).values_list('day_of_week', flat=True)),
			{0, 1, 2, 3, 4},
		)

	def test_full_day_block_saves_entire_time_range_without_time_inputs(self):
		doctor = Doctor.objects.create(name='Dr. Away', specialty='Pediatrics')
		response = self.client.post(reverse('admin_dashboard'), {
			'tab': 'schedules',
			'doctor': doctor.id,
			'date': '2026-10-15',
			'full_day': 'on',
			'reason': 'Hospital meeting',
			'save_blocked': '1',
		})

		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=schedules')
		blocked_slot = BlockedSlot.objects.get(doctor=doctor)
		self.assertEqual(blocked_slot.start_time, time(0, 0))
		self.assertEqual(blocked_slot.end_time, time(23, 59))
		self.assertEqual(blocked_slot.reason, 'Hospital meeting')

	def test_schedule_can_be_edited_and_deleted(self):
		doctor = Doctor.objects.create(name='Dr. Change', specialty='Internal Medicine')
		schedule = DoctorSchedule.objects.create(
			doctor=doctor,
			day_of_week=0,
			start_time='09:00',
			end_time='17:00',
			slot_duration=30,
		)
		response = self.client.post(reverse('admin_dashboard'), {
			'edit_schedule': schedule.id,
			'doctor': doctor.id,
			'days_of_week': ['1', '2'],
			'start_time': '10:00',
			'end_time': '16:00',
			'slot_duration': '20',
			'save_schedule': '1',
		})

		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=schedules')
		updated_schedules = DoctorSchedule.objects.filter(doctor=doctor)
		self.assertEqual(set(updated_schedules.values_list('day_of_week', flat=True)), {1, 2})
		self.assertEqual(set(updated_schedules.values_list('slot_duration', flat=True)), {20})

		schedule_to_delete = updated_schedules.first()
		response = self.client.post(reverse('schedule_delete', args=[schedule_to_delete.id]))
		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=schedules')
		self.assertEqual(DoctorSchedule.objects.filter(doctor=doctor).count(), 1)

	def test_upcoming_block_can_be_removed(self):
		doctor = Doctor.objects.create(name='Dr. Available', specialty='Surgery')
		blocked_slot = BlockedSlot.objects.create(
			doctor=doctor,
			date='2026-10-15',
			start_time='12:00',
			end_time='13:00',
			reason='Hospital meeting',
		)

		response = self.client.post(reverse('blocked_slot_delete', args=[blocked_slot.id]))
		self.assertRedirects(response, reverse('admin_dashboard') + '?tab=schedules')
		self.assertFalse(BlockedSlot.objects.filter(pk=blocked_slot.id).exists())
