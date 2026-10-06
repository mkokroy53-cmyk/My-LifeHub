from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def private_pdf_upload_path(instance, filename):
	return f'private_uploads/{instance.user_id}/{uuid4().hex}.pdf'


class DashboardEntry(models.Model):
	class Kind(models.TextChoices):
		DIARY = 'diary', 'Diary entry'
		NOTE = 'note', 'Note'
		RESOURCE = 'resource', 'Learning resource'
		PROJECT = 'project', 'Project'
		GOAL = 'goal', 'Goal'
		ACHIEVEMENT = 'achievement', 'Achievement'
		MEMORY = 'memory', 'Memory'
		ENTERTAINMENT = 'entertainment', 'Entertainment'
		IDEA = 'idea', 'Idea'

	class Status(models.TextChoices):
		NEW = 'new', 'New'
		IN_PROGRESS = 'in_progress', 'In progress'
		COMPLETED = 'completed', 'Completed'
		CANCELLED = 'cancelled', 'Cancelled'

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_entries')
	kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
	title = models.CharField(max_length=180)
	description = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
	progress = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
	target_date = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']
		indexes = [models.Index(fields=['user', 'kind', '-updated_at'])]

	def __str__(self):
		return self.title


class DashboardScheduleItem(models.Model):
	class Kind(models.TextChoices):
		TIMETABLE = 'timetable', 'Timetable'
		DEADLINE = 'deadline', 'Deadline'
		EVENT = 'event', 'Event'
		REMINDER = 'reminder', 'Reminder'

	WEEKDAYS = [
		(0, 'Monday'),
		(1, 'Tuesday'),
		(2, 'Wednesday'),
		(3, 'Thursday'),
		(4, 'Friday'),
		(5, 'Saturday'),
		(6, 'Sunday'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_schedule_items')
	kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True)
	title = models.CharField(max_length=180)
	description = models.TextField(blank=True)
	date = models.DateField(null=True, blank=True, db_index=True)
	weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS, null=True, blank=True)
	start_time = models.TimeField(null=True, blank=True)
	end_time = models.TimeField(null=True, blank=True)
	location = models.CharField(max_length=160, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['date', 'start_time', 'title']
		indexes = [models.Index(fields=['user', 'kind', 'date'])]

	def __str__(self):
		return self.title


class DashboardQuote(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_quotes')
	text = models.CharField(max_length=500)
	author = models.CharField(max_length=160, blank=True)
	is_favorite = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.text[:80]


class PrivatePDFUpload(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='private_pdf_uploads')
	original_filename = models.CharField(max_length=255)
	file = models.FileField(upload_to=private_pdf_upload_path)
	file_size = models.PositiveIntegerField()
	uploaded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-uploaded_at']

	def __str__(self):
		return self.original_filename
