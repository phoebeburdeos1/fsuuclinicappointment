from django.urls import path

from .views import (
    book_appointment,
    archive_appointment,
    cancel_appointment,
    doctor_slot_availability,
    my_appointments,
    patient_dashboard,
    reschedule_appointment,
    restore_appointment,
    update_profile,
)

urlpatterns = [
    path('', patient_dashboard, name='patient_dashboard'),
    path('appointments/', my_appointments, name='my_appointments'),
    path('appointments/slots/', doctor_slot_availability, name='doctor_slots'),
    path('appointments/book/', book_appointment, name='book_appointment'),
    path('appointments/<int:pk>/cancel/', cancel_appointment, name='cancel_appointment'),
    path('appointments/<int:pk>/archive/', archive_appointment, name='archive_appointment'),
    path('appointments/<int:pk>/restore/', restore_appointment, name='restore_appointment'),
    path('appointments/<int:pk>/reschedule/', reschedule_appointment, name='reschedule_appointment'),
    path('profile/', update_profile, name='profile_update'),
]
