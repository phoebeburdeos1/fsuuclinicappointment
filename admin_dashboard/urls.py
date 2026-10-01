from django.urls import path

from .views import (
    admin_dashboard,
    archive_appointment,
    appointment_status_update,
    delete_blocked_slot,
    delete_doctor,
    delete_schedule,
    doctor_form_view,
    restore_doctor,
    restore_appointment,
)

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('settings/', admin_dashboard, {'settings_page': True}, name='admin_settings'),
    path('doctor/new/', doctor_form_view, name='doctor_new'),
    path('doctor/<int:pk>/edit/', doctor_form_view, name='doctor_edit'),
    path('doctor/<int:pk>/archive/', delete_doctor, name='doctor_delete'),
    path('doctor/<int:pk>/restore/', restore_doctor, name='doctor_restore'),
    path('schedule/<int:pk>/delete/', delete_schedule, name='schedule_delete'),
    path('blocked-slot/<int:pk>/delete/', delete_blocked_slot, name='blocked_slot_delete'),
    path('appointment/<int:pk>/archive/', archive_appointment, name='appointment_archive'),
    path('appointment/<int:pk>/restore/', restore_appointment, name='appointment_restore'),
    path('appointment/<int:pk>/status/', appointment_status_update, name='appointment_status_update'),
]
