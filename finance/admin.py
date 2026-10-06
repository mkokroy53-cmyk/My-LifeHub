from django.contrib import admin

from .models import FinanceTransaction


@admin.register(FinanceTransaction)
class FinanceTransactionAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'amount', 'currency', 'category', 'date', 'user']
    list_filter = ['kind', 'currency', 'category', 'date']
    search_fields = ['title', 'notes', 'user__username']
    ordering = ['-date', '-created_at']
