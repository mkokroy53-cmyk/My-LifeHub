from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


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

	class Status(models.TextChoices):
		NEW = 'new', 'New'
		IN_PROGRESS = 'in_progress', 'In progress'
		COMPLETED = 'completed', 'Completed'
		CANCELLED = 'cancelled', 'Cancelled'

	class Mood(models.TextChoices):
		GREAT = 'great', 'Great'
		GOOD = 'good', 'Good'
		NEUTRAL = 'neutral', 'Neutral'
		LOW = 'low', 'Low'
		ROUGH = 'rough', 'Rough'

	class Priority(models.TextChoices):
		LOW = 'low', 'Low'
		MEDIUM = 'medium', 'Medium'
		HIGH = 'high', 'High'
		CRITICAL = 'critical', 'Critical'

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_entries')
	kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
	title = models.CharField(max_length=180)
	description = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
	progress = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
	target_date = models.DateField(null=True, blank=True)
	mood = models.CharField(max_length=12, choices=Mood.choices, blank=True)
	is_pinned = models.BooleanField(default=False)

	# Project-specific fields
	priority = models.CharField(max_length=10, choices=Priority.choices, blank=True)
	role = models.CharField(max_length=120, blank=True)
	client = models.CharField(max_length=120, blank=True)
	period_start = models.DateField(null=True, blank=True)
	period_end = models.DateField(null=True, blank=True)
	tech_stack = models.CharField(max_length=300, blank=True, help_text='Comma-separated technologies')
	repo_url = models.URLField(max_length=400, blank=True)
	live_url = models.URLField(max_length=400, blank=True)
	notes_url = models.URLField(max_length=400, blank=True)

	created_at = models.DateTimeField(auto_now_add=True, db_index=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']
		indexes = [models.Index(fields=['user', 'kind', '-updated_at'])]

	def __str__(self):
		return self.title

	@property
	def tech_list(self):
		return [tech.strip() for tech in self.tech_stack.split(',') if tech.strip()]

	@property
	def period_label(self):
		if not self.period_start and not self.period_end:
			return ''
		start = self.period_start.strftime('%b %Y') if hasattr(self.period_start, 'strftime') else '?'
		if not self.period_end:
			end = 'Present'
		else:
			end = self.period_end.strftime('%b %Y') if hasattr(self.period_end, 'strftime') else '?'
		return f'{start} – {end}'

	@property
	def duration_label(self):
		if not hasattr(self.period_start, 'strftime'):
			return ''
		end = self.period_end if hasattr(self.period_end, 'strftime') else timezone.localdate()
		days = (end - self.period_start).days
		if days < 0:
			return ''
		months = max(1, int(days / 30 + 0.5))
		return f'{months} month{"s" if months != 1 else ""}'


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
	class Category(models.TextChoices):
		LECTURE = 'lecture', 'Lecture notes'
		TEXTBOOK = 'textbook', 'Textbook'
		ASSIGNMENT = 'assignment', 'Assignment'
		RESEARCH = 'research', 'Research paper'
		SLIDES = 'slides', 'Slides'
		EXAM = 'exam', 'Exam / past paper'
		OTHER = 'other', 'Other'

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='private_pdf_uploads')
	original_filename = models.CharField(max_length=255)
	title = models.CharField(max_length=200, blank=True)
	file = models.FileField(upload_to=private_pdf_upload_path)
	file_size = models.PositiveIntegerField()
	category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
	notes = models.TextField(blank=True)
	is_pinned = models.BooleanField(default=False)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-uploaded_at']

	def __str__(self):
		return self.title or self.original_filename

	@property
	def display_name(self):
		return self.title or self.original_filename
