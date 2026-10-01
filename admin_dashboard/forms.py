from django import forms

from accounts.models import User

from .models import Appointment, BlockedSlot, DayOfWeek, Doctor, DoctorSchedule


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


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
    days_of_week = forms.MultipleChoiceField(
        choices=[(value, label[:3]) for value, label in DayOfWeek.choices],
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )
    slot_duration = forms.IntegerField(
        min_value=5,
        max_value=180,
        initial=30,
        help_text='Recommended: 15–30 mins.',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DoctorSchedule
        fields = ['doctor', 'start_time', 'end_time', 'slot_duration']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select', 'data-doctor-select': 'schedule'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.filter(is_archived=False).order_by('name')
        if self.instance.pk and not self.is_bound:
            self.initial['days_of_week'] = [str(self.instance.day_of_week)]
        self.fields['start_time'].label = 'Start time'
        self.fields['end_time'].label = 'End time'

    def clean_days_of_week(self):
        return [int(day) for day in self.cleaned_data['days_of_week']]

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'End time must be later than start time.')
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            raise ValueError('Bulk schedule saves require commit=True.')

        if self.instance.pk:
            self.instance.delete()

        doctor = self.cleaned_data['doctor']
        start_time = self.cleaned_data['start_time']
        end_time = self.cleaned_data['end_time']
        slot_duration = self.cleaned_data['slot_duration']
        schedules = []
        for day in self.cleaned_data['days_of_week']:
            schedule, _ = DoctorSchedule.objects.update_or_create(
                doctor=doctor,
                day_of_week=day,
                start_time=start_time,
                end_time=end_time,
                defaults={'slot_duration': slot_duration},
            )
            schedules.append(schedule)
        return schedules


class BlockedSlotForm(forms.ModelForm):
    full_day = forms.BooleanField(required=False, label='Block Full Day')
    start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'data-block-time': 'start'}),
    )
    end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'data-block-time': 'end'}),
    )

    class Meta:
        model = BlockedSlot
        fields = ['doctor', 'date', 'start_time', 'end_time', 'reason']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select', 'data-doctor-select': 'blocked'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.filter(is_archived=False).order_by('name')
        self.fields['reason'].required = True
        self.fields['reason'].initial = ''

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('full_day'):
            cleaned_data['start_time'] = forms.TimeField().clean('00:00')
            cleaned_data['end_time'] = forms.TimeField().clean('23:59')
        else:
            start_time = cleaned_data.get('start_time')
            end_time = cleaned_data.get('end_time')
            if start_time and end_time and end_time <= start_time:
                self.add_error('end_time', 'End time must be later than start time.')
            elif not start_time:
                self.add_error('start_time', 'Enter a start time or choose full day.')
            elif not end_time:
                self.add_error('end_time', 'Enter an end time or choose full day.')
        return cleaned_data


class AppointmentFilterForm(forms.Form):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.all(), required=False, empty_label='All doctors')
    status = forms.ChoiceField(choices=[('', 'All statuses')] + Appointment.STATUS_CHOICES, required=False)
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
