from django.urls import path

from .views import admin_dashboard, appointment_status_update, delete_doctor, doctor_form_view, restore_doctor

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('doctor/new/', doctor_form_view, name='doctor_new'),
    path('doctor/<int:pk>/edit/', doctor_form_view, name='doctor_edit'),
    path('doctor/<int:pk>/archive/', delete_doctor, name='doctor_delete'),
    path('doctor/<int:pk>/restore/', restore_doctor, name='doctor_restore'),
    path('appointment/<int:pk>/status/', appointment_status_update, name='appointment_status_update'),
]
