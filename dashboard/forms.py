from pathlib import PurePosixPath

from django import forms

from .models import DashboardEntry, DashboardQuote, DashboardScheduleItem


class DashboardEntryForm(forms.ModelForm):
    class Meta:
        model = DashboardEntry
        fields = ['title', 'description', 'target_date', 'status', 'progress']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'progress': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'autofocus': True, 'maxlength': 180})
        if kind != DashboardEntry.Kind.GOAL:
            for field_name in ['target_date', 'status', 'progress']:
                self.fields.pop(field_name)


class DashboardScheduleForm(forms.ModelForm):
    class Meta:
        model = DashboardScheduleItem
        fields = ['title', 'description', 'date', 'weekday', 'start_time', 'end_time', 'location']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = kind
        self.fields['title'].widget.attrs.update({'autofocus': True, 'maxlength': 180})
        if kind == DashboardScheduleItem.Kind.TIMETABLE:
            self.fields.pop('date')
            self.fields['weekday'].required = True
            self.fields['start_time'].required = True
        else:
            self.fields.pop('weekday')
            self.fields['date'].required = True

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'End time must be later than start time.')
        return cleaned_data


class DashboardQuoteForm(forms.ModelForm):
    class Meta:
        model = DashboardQuote
        fields = ['text', 'author', 'is_favorite']
        widgets = {'text': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs.update({'autofocus': True, 'maxlength': 500})


class PrivatePDFUploadForm(forms.Form):
    pdf = forms.FileField(label='PDF file')

    def clean_pdf(self):
        uploaded_file = self.cleaned_data['pdf']
        if PurePosixPath(uploaded_file.name.replace('\\', '/')).suffix.lower() != '.pdf':
            raise forms.ValidationError('Choose a PDF file.')
        if uploaded_file.size > 15 * 1024 * 1024:
            raise forms.ValidationError('PDF files must be 15 MB or smaller.')
        header = uploaded_file.read(1024)
        uploaded_file.seek(0)
        if b'%PDF-' not in header:
            raise forms.ValidationError('This file does not have a valid PDF signature.')
        return uploaded_file