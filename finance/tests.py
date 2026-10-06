from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import FinanceTransaction


class FinanceAccessTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('finance:index'))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('finance:index')}")


class FinanceTransactionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='finance-owner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='finance-other', password='a-strong-test-password')
        self.client.force_login(self.user)

    def test_monthly_ledger_and_totals_are_private_and_currency_grouped(self):
        today = timezone.localdate()
        own_income = FinanceTransaction.objects.create(
            user=self.user,
            kind=FinanceTransaction.Kind.INCOME,
            title='Monthly salary',
            amount=Decimal('2500.00'),
            currency=FinanceTransaction.Currency.USD,
            category=FinanceTransaction.Category.SALARY,
            date=today,
        )
        FinanceTransaction.objects.create(
            user=self.user,
            kind=FinanceTransaction.Kind.EXPENSE,
            title='Train pass',
            amount=Decimal('45.50'),
            currency=FinanceTransaction.Currency.EUR,
            category=FinanceTransaction.Category.TRANSPORT,
            date=today,
        )
        FinanceTransaction.objects.create(
            user=self.other_user,
            kind=FinanceTransaction.Kind.EXPENSE,
            title='Private transaction',
            amount=Decimal('99.00'),
            currency=FinanceTransaction.Currency.USD,
            date=today,
        )

        response = self.client.get(reverse('finance:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_income.title)
        self.assertContains(response, 'Train pass')
        self.assertNotContains(response, 'Private transaction')
        summaries = {summary['currency']: summary for summary in response.context['currency_summaries']}
        self.assertEqual(summaries['USD']['income'], Decimal('2500.00'))
        self.assertEqual(summaries['EUR']['expense'], Decimal('45.50'))

    def test_new_transaction_is_saved_to_the_signed_in_user(self):
        response = self.client.post(
            reverse('finance:add'),
            {
                'kind': FinanceTransaction.Kind.EXPENSE,
                'title': 'Groceries',
                'amount': '32.40',
                'currency': FinanceTransaction.Currency.USD,
                'category': FinanceTransaction.Category.FOOD,
                'date': timezone.localdate().isoformat(),
                'notes': 'Weekly shop',
            },
        )

        self.assertRedirects(response, reverse('finance:index'))
        transaction = FinanceTransaction.objects.get(title='Groceries')
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.amount, Decimal('32.40'))

    def test_one_cent_is_a_valid_transaction_amount(self):
        response = self.client.post(
            reverse('finance:add'),
            {
                'kind': FinanceTransaction.Kind.EXPENSE,
                'title': 'Small purchase',
                'amount': '0.01',
                'currency': FinanceTransaction.Currency.USD,
                'category': FinanceTransaction.Category.OTHER,
                'date': timezone.localdate().isoformat(),
            },
        )

        self.assertRedirects(response, reverse('finance:index'))
        self.assertTrue(FinanceTransaction.objects.filter(user=self.user, amount=Decimal('0.01')).exists())

    def test_user_cannot_edit_or_delete_another_users_transaction(self):
        transaction = FinanceTransaction.objects.create(
            user=self.other_user,
            kind=FinanceTransaction.Kind.EXPENSE,
            title='Private transaction',
            amount=Decimal('12.00'),
        )

        edit_response = self.client.get(reverse('finance:edit', kwargs={'pk': transaction.pk}))
        delete_response = self.client.post(reverse('finance:delete', kwargs={'pk': transaction.pk}))

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(FinanceTransaction.objects.filter(pk=transaction.pk).exists())
