from django import forms

from .models import Appointment, BlockedSlot, Doctor, DoctorSchedule


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialty', 'sex', 'bio', 'photo']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'specialty': forms.TextInput(attrs={'class': 'form-control'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class DoctorScheduleForm(forms.ModelForm):
    slot_duration = forms.IntegerField(
        min_value=5,
        max_value=180,
        initial=30,
        help_text='Recommended: 15–30 minutes per patient slot for a smooth clinic flow.',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DoctorSchedule
        fields = ['doctor', 'day_of_week', 'start_time', 'end_time', 'slot_duration']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }


class BlockedSlotForm(forms.ModelForm):
    class Meta:
        model = BlockedSlot
        fields = ['doctor', 'date', 'start_time', 'end_time', 'reason']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AppointmentFilterForm(forms.Form):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.all(), required=False, empty_label='All doctors')
    status = forms.ChoiceField(choices=[('', 'All statuses')] + Appointment.STATUS_CHOICES, required=False)
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
