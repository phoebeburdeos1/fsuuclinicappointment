from datetime import date, datetime, timedelta

from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import patient_required
from accounts.models import Message, User, UserRole
from admin_dashboard.models import Appointment, BlockedSlot, Doctor, DoctorSchedule
from patient_dashboard.forms import BookingForm, SearchDoctorsForm


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'address', 'photo',
            'height_cm', 'weight_lbs', 'pulse_bpm', 'bmi', 'temperature_c',
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g. 169'}),
            'weight_lbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g. 140'}),
            'pulse_bpm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 72'}),
            'bmi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g. 22.4'}),
            'temperature_c': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g. 36.5'}),
        }


def generate_available_slots(doctor, appointment_date):
    slots = []
    weekday = appointment_date.weekday()
    schedules = DoctorSchedule.objects.filter(doctor=doctor, day_of_week=weekday)
    for schedule in schedules:
        start_dt = datetime.combine(appointment_date, schedule.start_time)
        end_dt = datetime.combine(appointment_date, schedule.end_time)
        current = start_dt
        while current + timedelta(minutes=schedule.slot_duration) <= end_dt:
            slot_end = current + timedelta(minutes=schedule.slot_duration)
            is_blocked = BlockedSlot.objects.filter(
                doctor=doctor,
                date=appointment_date,
            ).filter(
                start_time__lt=slot_end.time(),
                end_time__gt=current.time(),
            ).exists()
            existing = Appointment.objects.filter(doctor=doctor, date=appointment_date, time=current.time()).exists()
            if not is_blocked and not existing:
                slots.append(current.time())
            current += timedelta(minutes=schedule.slot_duration)
    return sorted(slots)


@patient_required
def patient_dashboard(request):
    form = SearchDoctorsForm(request.GET or None)
    doctors = [doctor for doctor in Doctor.objects.filter(is_archived=False).order_by('name') if doctor.is_publicly_visible()]
    appointments = Appointment.objects.filter(patient=request.user).select_related('doctor').order_by('date', 'time')
    today = timezone.localdate()
    current_time = timezone.localtime().time().replace(tzinfo=None)
    for doctor in doctors:
        today_slots = generate_available_slots(doctor, today)
        doctor.available_today = any(slot > current_time for slot in today_slots)

    specialty = request.GET.get('specialty') or ''
    doctor_name = request.GET.get('doctor_name') or ''
    if specialty:
        doctors = [doctor for doctor in doctors if specialty.lower() in doctor.specialty.lower()]
    if doctor_name:
        doctors = [doctor for doctor in doctors if doctor_name.lower() in doctor.name.lower()]

    selected_doctor = None
    selected_date = request.GET.get('date') or date.today().isoformat()
    selected_date_obj = date.fromisoformat(selected_date)
    doctor_id = request.GET.get('doctor_id')
    if doctor_id:
        selected_doctor = get_object_or_404(Doctor, pk=doctor_id)

    available_slots = generate_available_slots(selected_doctor, selected_date_obj) if selected_doctor else []

    active_future = appointments.filter(
        date__gte=date.today(),
    ).exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW, Appointment.Status.COMPLETED])
    upcoming_appointment = active_future.order_by('date', 'time').first()
    completed_visits = appointments.filter(status=Appointment.Status.COMPLETED).count()
    cancelled_visits = appointments.filter(status=Appointment.Status.CANCELLED).count()
    active_prescriptions = []
    active_appointments = appointments.filter(
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED, Appointment.Status.CHECKED_IN],
    )
    for appointment in active_appointments:
        for medication in appointment.medications_used or []:
            if isinstance(medication, dict):
                active_prescriptions.append({
                    'name': medication.get('name', 'Medication'),
                    'dosage': medication.get('dosage', 'Follow clinician instructions'),
                    'days_left': medication.get('days_left'),
                })
            else:
                active_prescriptions.append({
                    'name': str(medication),
                    'dosage': 'Follow clinician instructions',
                    'days_left': None,
                })

    return render(
        request,
        'patient_dashboard/dashboard.html',
        {
            'form': form,
            'profile_form': ProfileForm(instance=request.user),
            'doctors': doctors,
            'appointments': appointments,
            'active_appointments': appointments.filter(patient_archived=False),
            'archived_appointments': appointments.filter(patient_archived=True),
            'selected_doctor': selected_doctor,
            'selected_date': selected_date,
            'available_slots': available_slots,
            'upcoming_appointment': upcoming_appointment,
            'upcoming_visits': active_future.count(),
            'completed_visits': completed_visits,
            'cancelled_visits': cancelled_visits,
            'active_prescriptions': active_prescriptions[:4],
        },
    )


@patient_required
def my_appointments(request):
    patient_appointments = Appointment.objects.filter(patient=request.user).select_related('doctor')
    appointments = patient_appointments.filter(patient_archived=False)
    archived_appointments = patient_appointments.filter(patient_archived=True)
    return render(request, 'patient_dashboard/my_appointments.html', {
        'appointments': appointments,
        'archived_appointments': archived_appointments,
        'all_appointments': patient_appointments,
    })


@patient_required
def archive_appointment(request, pk):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
        appointment.patient_archived = True
        appointment.save(update_fields=['patient_archived', 'updated_at'])
        messages.success(request, 'Appointment moved to your archive.')
    return redirect('my_appointments')


@patient_required
def restore_appointment(request, pk):
    if request.method == 'POST':
        appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
        appointment.patient_archived = False
        appointment.save(update_fields=['patient_archived', 'updated_at'])
        messages.success(request, 'Appointment restored to your list.')
    return redirect('my_appointments')


@patient_required
def doctor_slot_availability(request):
    doctor_id = request.GET.get('doctor_id')
    selected_date = request.GET.get('date')

    if not doctor_id or not selected_date:
        return JsonResponse({'slots': [], 'has_slots': False, 'message': 'Doctor and date are required.'})

    try:
        target_date = date.fromisoformat(selected_date)
    except ValueError:
        return JsonResponse({'slots': [], 'has_slots': False, 'message': 'Invalid date.'})

    doctor = get_object_or_404(Doctor, pk=doctor_id)
    slots = generate_available_slots(doctor, target_date)
    return JsonResponse({
        'doctor_id': doctor.id,
        'date': target_date.isoformat(),
        'slots': [slot.strftime('%H:%M') for slot in slots],
        'has_slots': bool(slots),
        'message': 'No available slots for this date. Please select another date.' if not slots else '',
    })


@patient_required
def book_appointment(request):
    if request.method != 'POST':
        return redirect('patient_dashboard')

    doctor_id = request.POST.get('doctor')
    selected_date = request.POST.get('date')
    selected_time = request.POST.get('time')
    notes = (request.POST.get('notes') or '').strip()
    visit_type = (request.POST.get('visit_type') or '').strip()

    if not notes:
        messages.error(request, 'Please provide a reason for your visit.')
        return redirect('patient_dashboard')

    if not all([doctor_id, selected_date, selected_time]):
        messages.error(request, 'Please choose a doctor, date, and time.')
        return redirect('patient_dashboard')

    target_date = date.fromisoformat(selected_date)
    target_time = datetime.strptime(selected_time, '%H:%M').time()
    formatted_notes = notes
    if visit_type:
        formatted_notes = f'{visit_type}: {notes}'

    with transaction.atomic():
        doctor = Doctor.objects.select_for_update().get(pk=doctor_id)
        available_slots = generate_available_slots(doctor, target_date)
        if target_time not in available_slots:
            messages.error(request, 'That slot is no longer available. Please choose another time.')
            return redirect('patient_dashboard')
        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            date=target_date,
            time=target_time,
            status=Appointment.Status.PENDING,
            notes=formatted_notes,
        )

        for recipient in User.objects.filter(role__in=[UserRole.ADMIN, UserRole.STAFF], is_active=True):
            Message.objects.create(
                sender=request.user,
                recipient=recipient,
                appointment=appointment,
                subject='New appointment booked',
                body=f'{request.user.get_full_name() or request.user.username} booked {doctor.name} on {target_date:%b %d, %Y} at {target_time:%I:%M %p}.',
            )

    messages.success(request, 'Appointment booked successfully.')
    return redirect('my_appointments')


@patient_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
    if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]:
        messages.warning(request, 'This appointment cannot be cancelled.')
        return redirect('my_appointments')
    if not appointment.can_cancel():
        messages.error(request, 'Appointments can no longer be cancelled within 2 hours of the visit time.')
        return redirect('my_appointments')

    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=['status'])
    messages.success(request, 'Appointment cancelled.')
    return redirect('my_appointments')


@patient_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
    if request.method == 'POST':
        new_date = date.fromisoformat(request.POST.get('date'))
        new_time = datetime.strptime(request.POST.get('time'), '%H:%M').time()
        with transaction.atomic():
            appointment = Appointment.objects.select_for_update().get(pk=pk, patient=request.user)
            available_slots = generate_available_slots(appointment.doctor, new_date)
            if new_time not in available_slots:
                messages.error(request, 'The requested slot is unavailable. Please choose a different time.')
                return redirect('my_appointments')
            appointment.date = new_date
            appointment.time = new_time
            appointment.status = Appointment.Status.PENDING
            appointment.save(update_fields=['date', 'time', 'status'])
        messages.success(request, 'Appointment rescheduled successfully.')
        return redirect('my_appointments')

    available_slots = generate_available_slots(appointment.doctor, appointment.date)
    return render(
        request,
        'patient_dashboard/reschedule_appointment.html',
        {'appointment': appointment, 'available_slots': available_slots},
    )


@patient_required
def update_profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('patient_dashboard')
    return render(request, 'patient_dashboard/profile.html', {'form': form})
