import json
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from accounts.decorators import admin_only_required, admin_required, staff_or_admin_required
from accounts.models import Message, UserRole

from .forms import AdminProfileForm, AppointmentFilterForm, BlockedSlotForm, DoctorForm, DoctorScheduleForm
from .models import Appointment, BlockedSlot, Doctor, DoctorSchedule, InventoryItem


@staff_or_admin_required
def admin_dashboard(request, settings_page=False):
    selected_doctor_id = request.GET.get('doctor_id')
    edit_schedule_id = request.POST.get('edit_schedule') if request.method == 'POST' else request.GET.get('edit_schedule')
    schedule_instance = get_object_or_404(DoctorSchedule, pk=edit_schedule_id) if edit_schedule_id else None
    doctor_form = DoctorForm(request.POST or None, request.FILES or None)
    schedule_form = DoctorScheduleForm(
        request.POST or None,
        initial={'doctor': selected_doctor_id} if selected_doctor_id else None,
        instance=schedule_instance,
    )
    blocked_form = BlockedSlotForm(request.POST or None)
    filter_form = AppointmentFilterForm(request.GET or None)

    if request.method == 'POST':
        settings_action = request.POST.get('settings_action')
        settings_url = reverse('admin_settings')
        if settings_action == 'save_profile':
            profile_form = AdminProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile details saved.')
            else:
                messages.error(request, 'Please correct the profile details and try again.')
            return redirect(settings_url + '?settings=profile')
        if settings_action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'The new passwords do not match.')
            else:
                try:
                    validate_password(new_password, request.user)
                except ValidationError as error:
                    messages.error(request, ' '.join(error.messages))
                else:
                    request.user.set_password(new_password)
                    request.user.save(update_fields=['password'])
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Password updated.')
            return redirect(settings_url + '?settings=profile')
        if settings_action == 'inventory_add':
            name = request.POST.get('name', '').strip()
            category = request.POST.get('category') or InventoryItem.Category.GENERAL_ITEMS
            try:
                quantity = max(0, int(request.POST.get('quantity', 0) or 0))
                unit_price = Decimal(request.POST.get('unit_price', '0') or '0')
            except (TypeError, ValueError, InvalidOperation):
                messages.error(request, 'Enter a valid stock quantity and price.')
                return redirect(settings_url + '?settings=inventory')
            if name:
                valid_categories = {choice[0] for choice in InventoryItem.Category.choices}
                if category not in valid_categories:
                    category = InventoryItem.Category.GENERAL_ITEMS
                InventoryItem.objects.create(name=name, category=category, quantity=quantity, unit_price=unit_price)
                messages.success(request, f'{name} added to inventory.')
            return redirect(settings_url + '?settings=inventory')
        if settings_action == 'inventory_change':
            item = get_object_or_404(InventoryItem, pk=request.POST.get('item_id'))
            try:
                amount = max(1, int(request.POST.get('quantity', 1) or 1))
            except (TypeError, ValueError):
                amount = 1
            if request.POST.get('operation') == 'remove':
                item.quantity = max(0, item.quantity - amount)
            else:
                item.quantity += amount
            item.save(update_fields=['quantity', 'updated_at'])
            messages.success(request, f'{item.name} stock updated.')
            return redirect(settings_url + '?settings=inventory')
        if settings_action == 'inventory_restock':
            item = get_object_or_404(InventoryItem, pk=request.POST.get('item_id'))
            try:
                quantity_received = int(request.POST.get('quantity_received', 0) or 0)
            except (TypeError, ValueError):
                quantity_received = 0
            if quantity_received <= 0:
                messages.error(request, 'Enter a quantity greater than zero.')
                return redirect(settings_url + '?settings=restock')
            item.quantity += quantity_received
            item.save(update_fields=['quantity', 'updated_at'])
            messages.success(request, f'Added {quantity_received} units to {item.name}.')
            return redirect(settings_url + '?settings=restock')
        if settings_action == 'inventory_delete':
            item = get_object_or_404(InventoryItem, pk=request.POST.get('item_id'))
            item.delete()
            messages.success(request, 'Inventory item deleted.')
            return redirect(settings_url + '?settings=inventory')
        if 'save_doctor' in request.POST and doctor_form.is_valid():
            saved_doctor = doctor_form.save()
            schedule_url = reverse('admin_dashboard') + f'?tab=schedules&doctor_id={saved_doctor.id}'
            link = mark_safe(f'<a href="{schedule_url}" class="btn btn-sm btn-light ms-2 mt-1"><i class="bi bi-plus-circle me-1"></i>Add Working Schedule for {saved_doctor.name}</a>')
            messages.success(request, mark_safe(f'Doctor saved! {link}'))
            return redirect(f"{reverse('admin_dashboard')}?tab=schedules&doctor_id={saved_doctor.id}")
        if 'save_schedule' in request.POST and schedule_form.is_valid():
            with transaction.atomic():
                schedules_saved = schedule_form.save()
            messages.success(request, f'{len(schedules_saved)} weekly schedule(s) saved.')
            return redirect(reverse('admin_dashboard') + '?tab=schedules')
        if 'save_blocked' in request.POST and blocked_form.is_valid():
            blocked_form.save()
            messages.success(request, 'Blocked slot created.')
            return redirect(reverse('admin_dashboard') + '?tab=schedules')

    appointments = Appointment.objects.select_related('patient', 'doctor').filter(is_archived=False)
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
    archived_appointments = Appointment.objects.select_related('patient', 'doctor').filter(is_archived=True)
    schedules = DoctorSchedule.objects.select_related('doctor').filter(doctor__is_archived=False)
    blocked_slots = BlockedSlot.objects.select_related('doctor').filter(
        doctor__is_archived=False,
        date__gte=timezone.localdate(),
    )
    today = timezone.localdate()
    current_time = timezone.localtime().time()
    doctor_availability = []
    for doctor in doctors:
        today_schedules = doctor.schedules.filter(day_of_week=today.weekday())
        if not today_schedules.exists():
            availability_status = 'Available'
        elif today_schedules.filter(start_time__lte=current_time, end_time__gte=current_time).exists():
            availability_status = 'In Session'
        elif today_schedules.filter(end_time__gt=current_time).exists():
            availability_status = 'Available'
        else:
            availability_status = 'Off'
        doctor_availability.append({
            'doctor': doctor,
            'status': availability_status,
        })

    total_appointments = appointments.count()
    no_show_rate = round((appointments.filter(status=Appointment.Status.NO_SHOW).count() / total_appointments) * 100, 2) if total_appointments else 0
    per_doctor = list(Appointment.objects.filter(is_archived=False).values('doctor__name').annotate(count=Count('id')).order_by('-count'))
    daily_counts = list(Appointment.objects.filter(is_archived=False).values('date').annotate(count=Count('id')).order_by('date')[:7])
    slot_counts = list(Appointment.objects.filter(is_archived=False).values('time').annotate(count=Count('id')).order_by('-count')[:8])
    low_stock_items = InventoryItem.objects.filter(quantity__lte=10).order_by('quantity')
    medication_items = InventoryItem.objects.filter(category=InventoryItem.Category.MEDICATION).order_by('name')
    consumable_items = InventoryItem.objects.filter(category=InventoryItem.Category.CONSUMABLES).order_by('name')
    inventory_items = InventoryItem.objects.all().order_by('name')
    profile_form = AdminProfileForm(instance=request.user)

    context = {
        'doctors': doctors,
        'doctor_availability': doctor_availability,
        'archived_doctors': archived_doctors,
        'archived_appointments': archived_appointments,
        'schedules': schedules,
        'blocked_slots': blocked_slots,
        'appointments': appointments,
        'doctor_form': doctor_form,
        'schedule_form': schedule_form,
        'edit_schedule_id': schedule_instance.pk if schedule_instance else None,
        'blocked_form': blocked_form,
        'filter_form': filter_form,
        'total_appointments': total_appointments,
        'no_show_rate': no_show_rate,
        'per_doctor': per_doctor,
        'daily_counts': daily_counts,
        'slot_counts': slot_counts,
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_items.count(),
        'medication_items': medication_items,
        'consumable_items': consumable_items,
        'inventory_items': inventory_items,
        'profile_form': profile_form,
        'settings_tab': request.GET.get('settings', 'archives'),
        'settings_page': settings_page,
        'doctor_chart_data': json.dumps([item['doctor__name'] for item in per_doctor]),
        'doctor_chart_counts': json.dumps([item['count'] for item in per_doctor]),
        'daily_labels': json.dumps([item['date'].strftime('%Y-%m-%d') for item in daily_counts]),
        'daily_values': json.dumps([item['count'] for item in daily_counts]),
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


@admin_only_required
@require_POST
def delete_schedule(request, pk):
    schedule = get_object_or_404(DoctorSchedule, pk=pk)
    schedule.delete()
    messages.success(request, 'Weekly schedule removed.')
    return redirect(reverse('admin_dashboard') + '?tab=schedules')


@admin_only_required
@require_POST
def delete_blocked_slot(request, pk):
    blocked_slot = get_object_or_404(BlockedSlot, pk=pk)
    blocked_slot.delete()
    messages.success(request, 'Blocked time removed.')
    return redirect(reverse('admin_dashboard') + '?tab=schedules')


@staff_or_admin_required
def staff_dashboard(request):
    today = timezone.now().date()
    today_appointments = Appointment.objects.filter(date=today).select_related('patient', 'doctor')
    checked_in_count = today_appointments.filter(status=Appointment.Status.CHECKED_IN).count()
    low_stock_items = InventoryItem.objects.filter(quantity__lt=10).order_by('quantity')
    unread_messages = 0

    medication_items = InventoryItem.objects.filter(category=InventoryItem.Category.MEDICATION).order_by('name')
    consumable_items = InventoryItem.objects.filter(category=InventoryItem.Category.CONSUMABLES).order_by('name')

    context = {
        'today_appointments': today_appointments,
        'today_appointments_count': today_appointments.count(),
        'checked_in_count': checked_in_count,
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_items.count(),
        'unread_messages': unread_messages,
        'medication_items': medication_items,
        'consumable_items': consumable_items,
    }
    return render(request, 'admin_dashboard/staff_dashboard.html', context)


@staff_or_admin_required
def inventory_view(request):
    items = InventoryItem.objects.all().order_by('name')
    low_stock_items = items.filter(quantity__lt=10)
    out_of_stock_count = items.filter(quantity=0).count()

    if request.method == 'POST':
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')
        if action and item_id:
            item = get_object_or_404(InventoryItem, pk=item_id)
            if action == 'add':
                item.quantity += int(request.POST.get('quantity', 0) or 0)
            elif action == 'remove':
                item.quantity = max(0, item.quantity - int(request.POST.get('quantity', 0) or 0))
            elif action == 'delete':
                item.delete()
                messages.success(request, f'{item.name} was removed from inventory.')
                return redirect('inventory')
            item.save(update_fields=['quantity', 'updated_at'])
            messages.success(request, f'{item.name} updated successfully.')
            return redirect('inventory')

        name = request.POST.get('name', '').strip()
        category = request.POST.get('category') or InventoryItem.Category.GENERAL_ITEMS
        quantity = int(request.POST.get('quantity', 0) or 0)
        unit_price = request.POST.get('unit_price', 0)
        if name:
            InventoryItem.objects.create(name=name, category=category, quantity=quantity, unit_price=unit_price)
            messages.success(request, f'{name} added to inventory.')
            return redirect('inventory')

    context = {
        'items': items,
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_items.count(),
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'admin_dashboard/inventory.html', context)


@admin_only_required
def doctor_form_view(request, pk=None):
    doctor = get_object_or_404(Doctor, pk=pk) if pk else None
    form = DoctorForm(request.POST or None, request.FILES or None, instance=doctor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Doctor profile updated.')
        return redirect('admin_dashboard')
    return render(request, 'admin_dashboard/doctor_form.html', {'form': form, 'doctor': doctor})


@admin_only_required
def delete_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_archived = True
    doctor.archived_at = timezone.now()
    doctor.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, f'{doctor.name} has been archived.')
    return redirect('admin_dashboard')


@admin_only_required
def restore_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    doctor.is_archived = False
    doctor.archived_at = None
    doctor.save(update_fields=['is_archived', 'archived_at'])
    messages.success(request, f'{doctor.name} has been restored.')
    return redirect('admin_settings')


@admin_only_required
@require_POST
def archive_appointment(request, pk):
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        status=Appointment.Status.COMPLETED,
        is_archived=False,
    )
    appointment.is_archived = True
    appointment.save(update_fields=['is_archived', 'updated_at'])
    messages.success(request, 'Appointment record archived.')
    return redirect(reverse('admin_dashboard') + '?tab=appointments')


@admin_only_required
@require_POST
def restore_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, is_archived=True)
    appointment.is_archived = False
    appointment.save(update_fields=['is_archived', 'updated_at'])
    messages.success(request, 'Appointment restored to the active timeline.')
    return redirect(reverse('admin_dashboard') + '?tab=appointments')


@staff_or_admin_required
def appointment_status_update(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, is_archived=False)
    previous_status = appointment.status
    new_status = request.POST.get('status')
    valid_statuses = [choice[0] for choice in Appointment.Status.choices]
    if new_status in valid_statuses:
        appointment.status = new_status
        if new_status == Appointment.Status.COMPLETED:
            diagnosis = (request.POST.get('diagnosis') or '').strip()
            appointment.medical_summary = diagnosis or appointment.medical_summary or 'No diagnosis recorded.'
            appointment.consultation_fee = 1000.00

            medication_ids = request.POST.getlist('medication_ids')
            medication_quantities = request.POST.getlist('medication_quantities')
            medication_entries = []
            for index, item_id in enumerate(medication_ids):
                if not item_id:
                    continue
                try:
                    item = InventoryItem.objects.get(pk=item_id)
                except InventoryItem.DoesNotExist:
                    continue
                try:
                    quantity_used = int(medication_quantities[index]) if index < len(medication_quantities) else 0
                except (TypeError, ValueError):
                    continue
                if quantity_used > 0:
                    medication_entries.append({'name': item.name, 'quantity': quantity_used})
                    item.quantity = max(0, item.quantity - quantity_used)
                    item.save(update_fields=['quantity', 'updated_at'])
                    messages.success(request, f'{item.name} stock updated by {quantity_used}.')
            appointment.medications_used = medication_entries

            supply_ids = request.POST.getlist('supply_ids')
            supply_quantities = request.POST.getlist('supply_quantities')
            supply_entries = []
            for index, item_id in enumerate(supply_ids):
                if not item_id:
                    continue
                try:
                    item = InventoryItem.objects.get(pk=item_id)
                except InventoryItem.DoesNotExist:
                    continue
                try:
                    quantity_used = int(supply_quantities[index]) if index < len(supply_quantities) else 0
                except (TypeError, ValueError):
                    continue
                if quantity_used > 0:
                    supply_entries.append({'name': item.name, 'quantity': quantity_used})
                    item.quantity = max(0, item.quantity - quantity_used)
                    item.save(update_fields=['quantity', 'updated_at'])
                    messages.success(request, f'{item.name} supply stock updated by {quantity_used}.')
            appointment.supplies_used = supply_entries

        appointment.save(update_fields=['status', 'notes', 'medical_summary', 'consultation_fee', 'medications_used', 'supplies_used'])
        if new_status != previous_status:
            Message.objects.create(
                sender=request.user,
                recipient=appointment.patient,
                appointment=appointment,
                subject='Appointment status updated',
                body=f'Your appointment with {appointment.doctor.name} on {appointment.date:%b %d, %Y} at {appointment.time:%I:%M %p} is now {appointment.get_status_display()}.',
            )
        messages.success(request, f'Appointment marked as {new_status}.')
    next_url = 'staff_dashboard' if request.user.role == UserRole.STAFF else 'admin_dashboard'
    return redirect(next_url)
