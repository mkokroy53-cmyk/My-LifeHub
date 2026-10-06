from django.contrib import admin

from .models import DashboardEntry, DashboardQuote, DashboardScheduleItem, PrivatePDFUpload


@admin.register(DashboardEntry)
class DashboardEntryAdmin(admin.ModelAdmin):
	list_display = ['title', 'kind', 'status', 'user', 'updated_at']
	list_filter = ['kind', 'status', 'updated_at']
	search_fields = ['title', 'description', 'user__username']
	ordering = ['-updated_at']


@admin.register(DashboardScheduleItem)
class DashboardScheduleItemAdmin(admin.ModelAdmin):
	list_display = ['title', 'kind', 'date', 'weekday', 'start_time', 'user']
	list_filter = ['kind', 'date', 'weekday']
	search_fields = ['title', 'description', 'location', 'user__username']
	ordering = ['date', 'start_time']


@admin.register(DashboardQuote)
class DashboardQuoteAdmin(admin.ModelAdmin):
	list_display = ['text', 'author', 'is_favorite', 'user', 'created_at']
	list_filter = ['is_favorite', 'created_at']
	search_fields = ['text', 'author', 'user__username']
	ordering = ['-created_at']


@admin.register(PrivatePDFUpload)
class PrivatePDFUploadAdmin(admin.ModelAdmin):
	list_display = ['original_filename', 'file_size', 'user', 'uploaded_at']
	list_filter = ['uploaded_at']
	search_fields = ['original_filename', 'user__username']
	ordering = ['-uploaded_at']
