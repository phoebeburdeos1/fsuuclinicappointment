from django import forms

from admin_dashboard.models import Doctor


class SearchDoctorsForm(forms.Form):
    specialty = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by specialty'}))
    doctor_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by doctor name'}))


class BookingForm(forms.Form):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}))
    visit_type = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select a visit type'),
            ('General Consultation', 'General Consultation'),
            ('Follow-up Visit', 'Follow-up Visit'),
            ('Acute Symptoms / Fever', 'Acute Symptoms / Fever'),
            ('Routine Examination', 'Routine Examination'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=True,
        error_messages={'required': 'Please provide a reason for your visit.'},
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'required': 'required'}),
    )
