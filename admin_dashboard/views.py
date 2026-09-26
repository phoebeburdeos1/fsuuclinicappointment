import json
from collections import Counter
from datetime import datetime

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from accounts.decorators import admin_required

from .forms import AppointmentFilterForm, BlockedSlotForm, DoctorForm, DoctorScheduleForm
from .models import Appointment, BlockedSlot, Doctor, DoctorSchedule


@admin_required
def admin_dashboard(request):
    selected_doctor_id = request.GET.get('doctor_id')
    doctor_form = DoctorForm(request.POST or None, request.FILES or None)
    schedule_form = DoctorScheduleForm(request.POST or None, initial={'doctor': selected_doctor_id} if selected_doctor_id else None)
    blocked_form = BlockedSlotForm(request.POST or None)
    filter_form = AppointmentFilterForm(request.GET or None)

    if request.method == 'POST':
        if 'save_doctor' in request.POST and doctor_form.is_valid():
            saved_doctor = doctor_form.save()
            schedule_url = reverse('admin_dashboard') + f'?tab=schedules&doctor_id={saved_doctor.id}'
            link = mark_safe(f'<a href="{schedule_url}" class="btn btn-sm btn-light ms-2 mt-1"><i class="bi bi-plus-circle me-1"></i>Add Working Schedule for {saved_doctor.name}</a>')
            messages.success(request, mark_safe(f'Doctor saved! {link}'))
            return redirect(f"{reverse('admin_dashboard')}?tab=schedules&doctor_id={saved_doctor.id}")
        if 'save_schedule' in request.POST and schedule_form.is_valid():
            schedule_form.save()
            messages.success(request, 'Doctor schedule saved.')
            return redirect('admin_dashboard')
        if 'save_blocked' in request.POST and blocked_form.is_valid():
            blocked_form.save()
            messages.success(request, 'Blocked slot created.')
            return redirect('admin_dashboard')

    appointments = Appointment.objects.select_related('patient', 'doctor').all()
    if filter_form.is_bound and filter_form.is_valid():
        doctor = filter_form.cleaned_data.get('doctor')
        status = filter_form.cleaned_data.get('status')
        date = filter_form.cleaned_data.get('date')
        if doctor:
            appointments = appointments.filter(doctor=doctor)
        if status:
            appointments = appointments.filter(status=status)
        if date:
            appointments = appointments.filter(date=date)

    doctors = Doctor.objects.filter(is_archived=False)
    archived_doctors = Doctor.objects.filter(is_archived=True)
    schedules = DoctorSchedule.objects.select_related('doctor').all()
    blocked_slots = BlockedSlot.objects.select_related('doctor').all()

    total_appointments = appointments.count()
    no_show_rate = round((appointments.filter(status=Appointment.Status.NO_SHOW).count() / total_appointments) * 100, 2) if total_appointments else 0
    per_doctor = list(Appointment.objects.values('doctor__name').annotate(count=Count('id')).order_by('-count'))
    daily_counts = list(Appointment.objects.values('date').annotate(count=Count('id')).order_by('date')[:7])
    slot_counts = list(Appointment.objects.values('time').annotate(count=Count('id')).order_by('-count')[:8])

    context = {
        'doctors': doctors,
        'archived_doctors': archived_doctors,
        'schedules': schedules,
        'blocked_slots': blocked_slots,
        'appointments': appointments,
        'doctor_form': doctor_form,
        'schedule_form': schedule_form,
        'blocked_form': blocked_form,
        'filter_form': filter_form,
        'total_appointments': total_appointments,
        'no_show_rate': no_show_rate,
        'per_doctor': per_doctor,
        'daily_counts': daily_counts,
        'slot_counts': slot_counts,
        'doctor_chart_data': json.dumps([item['doctor__name'] for item in per_doctor]),
        'doctor_chart_counts': json.dumps([item['count'] for item in per_doctor]),
        'daily_labels': json.dumps([item['date'].strftime('%Y-%m-%d') for item in daily_counts]),
        'daily_values': json.dumps([item['count'] for item in daily_counts]),
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


@admin_required
def doctor_form_view(request, pk=None):
    doctor = get_object_or_404(Doctor, pk=pk) if pk else None
    form = DoctorForm(request.POST or None, request.FILES or None, instance=doctor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Doctor profile updated.')
        return redirect('admin_dashboard')
    return render(request, 'admin_dashboard/doctor_form.html', {'form': form, 'doctor': doctor})


@admin_required
def delete_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_archived = True
    doctor.archived_at = timezone.now()
    doctor.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, f'{doctor.name} has been archived.')
    return redirect('admin_dashboard')


@admin_required
def restore_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_archived = False
    doctor.archived_at = None
    doctor.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, f'{doctor.name} has been restored.')
    return redirect('admin_dashboard')


@admin_required
def appointment_status_update(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get('status')
    valid_statuses = [choice[0] for choice in Appointment.Status.choices]
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save(update_fields=['status'])
        messages.success(request, f'Appointment marked as {new_status}.')
    return redirect('admin_dashboard')
