from django import forms

from .models import FinanceTransaction


class FinanceTransactionForm(forms.ModelForm):
    class Meta:
        model = FinanceTransaction
        fields = ['kind', 'title', 'amount', 'currency', 'category', 'date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01', 'inputmode': 'decimal'}),
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'autofocus': True, 'maxlength': 160})
        self.fields['amount'].help_text = 'Enter a positive amount; totals are kept separate by currency.'
