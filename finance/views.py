import calendar
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FinanceTransactionForm
from .models import FinanceTransaction


@login_required
def index(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not 1900 <= year <= 9998 or not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    month_start = today.replace(year=year, month=month, day=1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    previous_year, previous_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_start = month_start.replace(year=next_year, month=next_month, day=1)

    base_queryset = FinanceTransaction.objects.filter(
        user=request.user,
        date__gte=month_start,
        date__lt=next_start,
    )
    query = request.GET.get('q', '').strip()
    kind = request.GET.get('kind', '').strip()
    transactions = base_queryset
    if query:
        transactions = transactions.filter(Q(title__icontains=query) | Q(notes__icontains=query))
    if kind in FinanceTransaction.Kind.values:
        transactions = transactions.filter(kind=kind)
    page = Paginator(transactions, 25).get_page(request.GET.get('page'))

    totals = base_queryset.values('currency', 'kind').annotate(total=Sum('amount')).order_by('currency', 'kind')
    summaries_by_currency = {}
    for row in totals:
        summary = summaries_by_currency.setdefault(
            row['currency'],
            {'currency': row['currency'], 'income': Decimal('0.00'), 'expense': Decimal('0.00')},
        )
        summary[row['kind']] = row['total']
    currency_summaries = [
        {**summary, 'balance': summary['income'] - summary['expense']}
        for _currency, summary in sorted(summaries_by_currency.items())
    ]

    return render(
        request,
        'finance/index.html',
        {
            'transactions': page,
            'query': query,
            'selected_kind': kind,
            'month_label': calendar.month_name[month],
            'year': year,
            'month': month,
            'previous_year': previous_year,
            'previous_month': previous_month,
            'next_year': next_year,
            'next_month': next_month,
            'currency_summaries': currency_summaries,
            'kind_choices': FinanceTransaction.Kind.choices,
        },
    )


@login_required
def add(request):
    if request.method == 'POST':
        form = FinanceTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, 'Transaction saved.')
            return redirect('finance:index')
    else:
        form = FinanceTransactionForm()
    return render(request, 'finance/transaction_form.html', {'form': form, 'page_title': 'Add transaction'})


@login_required
def edit(request, pk):
    transaction = get_object_or_404(FinanceTransaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = FinanceTransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated.')
            return redirect('finance:index')
    else:
        form = FinanceTransactionForm(instance=transaction)
    return render(
        request,
        'finance/transaction_form.html',
        {'form': form, 'page_title': 'Edit transaction', 'transaction': transaction},
    )


@login_required
def delete(request, pk):
    transaction = get_object_or_404(FinanceTransaction, pk=pk, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted.')
        return redirect('finance:index')
    return render(request, 'finance/transaction_confirm_delete.html', {'transaction': transaction})
