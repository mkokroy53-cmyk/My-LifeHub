from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class FinanceTransaction(models.Model):
    class Kind(models.TextChoices):
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'

    class Currency(models.TextChoices):
        USD = 'USD', 'US dollar'
        EUR = 'EUR', 'Euro'
        GBP = 'GBP', 'Pound sterling'
        CAD = 'CAD', 'Canadian dollar'
        AUD = 'AUD', 'Australian dollar'
        INR = 'INR', 'Indian rupee'
        JPY = 'JPY', 'Japanese yen'
        CHF = 'CHF', 'Swiss franc'
        NZD = 'NZD', 'New Zealand dollar'
        KES = 'KES', 'Kenyan shilling'

    class Category(models.TextChoices):
        SALARY = 'salary', 'Salary'
        FREELANCE = 'freelance', 'Freelance'
        INVESTMENT = 'investment', 'Investment'
        HOUSING = 'housing', 'Housing'
        FOOD = 'food', 'Food'
        TRANSPORT = 'transport', 'Transport'
        HEALTH = 'health', 'Health'
        EDUCATION = 'education', 'Education'
        BILLS = 'bills', 'Bills'
        SHOPPING = 'shopping', 'Shopping'
        TRAVEL = 'travel', 'Travel'
        GIFT = 'gift', 'Gift'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='finance_transactions',
    )
    kind = models.CharField(max_length=8, choices=Kind.choices, db_index=True)
    title = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
    date = models.DateField(default=timezone.localdate, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['user', 'date']), models.Index(fields=['user', 'kind', 'date'])]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='finance_amount_positive')]

    def __str__(self):
        return self.title
