import calendar as month_calendar
import json
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from finance.models import FinanceTransaction

from .forms import DashboardEntryForm, DashboardQuoteForm, DashboardScheduleForm, PrivatePDFUploadForm
from .models import DashboardEntry, DashboardQuote, DashboardScheduleItem, PrivatePDFUpload


ENTRY_STATS = [
    (DashboardEntry.Kind.DIARY, 'Diary entries', 'icon-coral'),
    (DashboardEntry.Kind.NOTE, 'Notes', 'icon-blue'),
    (DashboardEntry.Kind.RESOURCE, 'Learning resources', 'icon-lime'),
    (DashboardEntry.Kind.PROJECT, 'Projects', 'icon-blue'),
    (DashboardEntry.Kind.GOAL, 'Goals', 'icon-lime'),
    (DashboardEntry.Kind.ACHIEVEMENT, 'Achievements', 'icon-coral'),
    (DashboardEntry.Kind.MEMORY, 'Memories', 'icon-blue'),
    (DashboardEntry.Kind.ENTERTAINMENT, 'Entertainment', 'icon-coral'),
    (DashboardEntry.Kind.IDEA, 'Ideas', 'icon-lime'),
]

MODULE_LABELS = {kind: label for kind, label, _ in ENTRY_STATS}
VALID_KINDS = {kind for kind, _label, _tone in ENTRY_STATS}

SCHEDULE_KINDS = {
    DashboardScheduleItem.Kind.TIMETABLE,
    DashboardScheduleItem.Kind.DEADLINE,
    DashboardScheduleItem.Kind.EVENT,
    DashboardScheduleItem.Kind.REMINDER,
}


def _pdf_archive_path(upload):
    filename = PurePosixPath(upload.original_filename.replace('\\', '/')).name
    return f'files/{upload.pk}-{filename}'


@login_required
def index(request):
    current_hour = timezone.localtime().hour
    greeting = 'Good morning' if current_hour < 12 else 'Good afternoon' if current_hour < 18 else 'Good evening'
    today = timezone.localdate()
    counts = dict(
        DashboardEntry.objects.filter(user=request.user)
        .values('kind')
        .annotate(total=Count('id'))
        .values_list('kind', 'total')
    )
    stats = [
        {
            'label': label,
            'count': counts.get(kind, 0),
            'tone': tone,
            'url': reverse('dashboard:entries_by_kind', kwargs={'kind': kind}),
        }
        for kind, label, tone in ENTRY_STATS
    ]
    quotes = list(DashboardQuote.objects.filter(user=request.user).order_by('id'))
    quote_of_day = quotes[today.toordinal() % len(quotes)] if quotes else None
    timetable = DashboardScheduleItem.objects.filter(
        user=request.user,
        kind=DashboardScheduleItem.Kind.TIMETABLE,
        weekday=today.weekday(),
    )
    upcoming = DashboardScheduleItem.objects.filter(
        user=request.user,
        kind__in=[
            DashboardScheduleItem.Kind.DEADLINE,
            DashboardScheduleItem.Kind.EVENT,
            DashboardScheduleItem.Kind.REMINDER,
        ],
        date__gte=today,
    ).order_by('date', 'start_time')[:5]
    return render(
        request,
        'dashboard/index.html',
        {
            'greeting': greeting,
            'today': today,
            'stats': stats,
            'recent_entries': DashboardEntry.objects.filter(user=request.user)[:6],
            'active_goals': DashboardEntry.objects.filter(
                user=request.user,
                kind=DashboardEntry.Kind.GOAL,
            ).exclude(status__in=[DashboardEntry.Status.COMPLETED, DashboardEntry.Status.CANCELLED])[:4],
            'quote_of_day': quote_of_day,
            'timetable': timetable,
            'upcoming': upcoming,
        },
    )


@login_required
def settings_view(request):
    return render(request, 'dashboard/settings.html')


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    entry_results = []
    if query:
        entry_results = list(
            DashboardEntry.objects.filter(user=request.user)
            .filter(Q(title__icontains=query) | Q(description__icontains=query))
            .order_by('-updated_at')[:20]
        )
    else:
        entry_results = list(DashboardEntry.objects.filter(user=request.user).order_by('-updated_at')[:20])

    schedule_results = []
    finance_results = []
    file_results = []
    if query:
        schedule_results = list(
            DashboardScheduleItem.objects.filter(user=request.user)
            .filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(location__icontains=query))
            .order_by('date', 'start_time')[:10]
        )
        finance_results = list(
            FinanceTransaction.objects.filter(user=request.user)
            .filter(Q(title__icontains=query) | Q(notes__icontains=query) | Q(category__icontains=query))
            .order_by('-date', '-created_at')[:20]
        )
        file_results = list(
            PrivatePDFUpload.objects.filter(user=request.user, original_filename__icontains=query)[:10]
        )

    total_count = len(entry_results) + len(schedule_results) + len(finance_results) + len(file_results)
    return render(
        request,
        'dashboard/search.html',
        {
            'query': query,
            'entry_results': entry_results,
            'schedule_results': schedule_results,
            'finance_results': finance_results,
            'file_results': file_results,
            'total_count': total_count,
        },
    )


@login_required
def calendar_view(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not 1900 <= year <= 9998 or not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    previous_year, previous_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    weeks = month_calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    visible_start, visible_end = weeks[0][0], weeks[-1][-1]

    dated_items = DashboardScheduleItem.objects.filter(
        user=request.user,
        date__gte=visible_start,
        date__lte=visible_end,
    ).exclude(kind=DashboardScheduleItem.Kind.TIMETABLE).order_by('start_time', 'title')
    items_by_date = {}
    for item in dated_items:
        items_by_date.setdefault(item.date, []).append(item)

    calendar_weeks = [
        [
            {
                'date': day,
                'in_month': day.month == month,
                'is_today': day == today,
                'items': items_by_date.get(day, []),
            }
            for day in week
        ]
        for week in weeks
    ]
    recurring_items = DashboardScheduleItem.objects.filter(
        user=request.user,
        kind=DashboardScheduleItem.Kind.TIMETABLE,
    ).order_by('weekday', 'start_time', 'title')

    return render(
        request,
        'dashboard/calendar.html',
        {
            'calendar_weeks': calendar_weeks,
            'month_label': month_calendar.month_name[month],
            'year': year,
            'month': month,
            'previous_year': previous_year,
            'previous_month': previous_month,
            'next_year': next_year,
            'next_month': next_month,
            'weekday_names': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'recurring_items': recurring_items,
            'weekdays': DashboardScheduleItem.WEEKDAYS,
        },
    )


@login_required
def library_overview(request):
    collections = []
    all_entries = DashboardEntry.objects.filter(user=request.user).order_by('-updated_at')[:12]
    for kind, label, tone in ENTRY_STATS:
        entries = DashboardEntry.objects.filter(user=request.user, kind=kind).order_by('-updated_at')[:3]
        collections.append({
            'kind': kind,
            'label': label,
            'tone': tone,
            'count': DashboardEntry.objects.filter(user=request.user, kind=kind).count(),
            'entries': entries,
        })
    return render(
        request,
        'dashboard/library.html',
        {'collections': collections, 'recent_entries': all_entries, 'page_title': 'Your life archive'},
    )


@login_required
def entries_by_kind(request, kind):
    if kind not in VALID_KINDS:
        messages.error(request, 'That item type is not available.')
        return redirect('dashboard:library')

    queryset = DashboardEntry.objects.filter(user=request.user, kind=kind).order_by('-updated_at')
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))

    return render(
        request,
        'dashboard/module_list.html',
        {
            'kind': kind,
            'kind_label': MODULE_LABELS[kind],
            'entries': queryset,
            'query': query,
            'count': queryset.count(),
        },
    )


@login_required
def entry_detail(request, kind, entry_id):
    if kind not in VALID_KINDS:
        messages.error(request, 'That item type is not available.')
        return redirect('dashboard:library')

    entry = get_object_or_404(DashboardEntry, user=request.user, kind=kind, pk=entry_id)
    return render(
        request,
        'dashboard/entry_detail.html',
        {'entry': entry, 'kind_label': MODULE_LABELS.get(kind, 'Record')},
    )


@login_required
def edit_entry(request, kind, entry_id):
    if kind not in VALID_KINDS:
        messages.error(request, 'That item type is not available.')
        return redirect('dashboard:library')

    entry = get_object_or_404(DashboardEntry, user=request.user, kind=kind, pk=entry_id)
    if request.method == 'POST':
        form = DashboardEntryForm(request.POST, instance=entry, kind=kind)
        if form.is_valid():
            updated_entry = form.save(commit=False)
            if kind == DashboardEntry.Kind.GOAL and updated_entry.status == DashboardEntry.Status.COMPLETED:
                updated_entry.progress = 100
            updated_entry.save()
            messages.success(request, f'{updated_entry.get_kind_display()} updated.')
            return redirect('dashboard:entry_detail', kind=kind, entry_id=entry.pk)
    else:
        form = DashboardEntryForm(instance=entry, kind=kind)

    return render(
        request,
        'dashboard/entry_form.html',
        {'form': form, 'item_title': entry.get_kind_display(), 'entry': entry, 'is_edit': True},
    )


@login_required
@require_http_methods(['GET', 'POST'])
def delete_entry(request, kind, entry_id):
    if kind not in VALID_KINDS:
        messages.error(request, 'That item type is not available.')
        return redirect('dashboard:library')

    entry = get_object_or_404(DashboardEntry, user=request.user, kind=kind, pk=entry_id)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, f'{entry.get_kind_display()} deleted.')
        return redirect('dashboard:entries_by_kind', kind=kind)
    return render(request, 'dashboard/entry_confirm_delete.html', {'entry': entry})


@login_required
def files(request):
    if request.method == 'POST':
        form = PrivatePDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['pdf']
            original_filename = PurePosixPath(uploaded_file.name.replace('\\', '/')).name[:255]
            PrivatePDFUpload.objects.create(
                user=request.user,
                original_filename=original_filename,
                file=uploaded_file,
                file_size=uploaded_file.size,
            )
            messages.success(request, 'Your PDF has been uploaded privately.')
            return redirect('dashboard:files')
    else:
        form = PrivatePDFUploadForm()
    return render(
        request,
        'dashboard/files.html',
        {'form': form, 'uploads': PrivatePDFUpload.objects.filter(user=request.user)},
    )


@login_required
def download_file(request, upload_id):
    upload = get_object_or_404(PrivatePDFUpload, user=request.user, pk=upload_id)
    if not upload.file or not upload.file.storage.exists(upload.file.name):
        raise Http404
    response = FileResponse(
        upload.file.open('rb'),
        as_attachment=True,
        filename=upload.original_filename,
        content_type='application/pdf',
    )
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
def delete_file(request, upload_id):
    upload = get_object_or_404(PrivatePDFUpload, user=request.user, pk=upload_id)
    if request.method == 'POST':
        upload.file.delete(save=False)
        upload.delete()
        messages.success(request, 'PDF deleted.')
        return redirect('dashboard:files')
    return render(request, 'dashboard/file_confirm_delete.html', {'upload': upload})


@login_required
def export(request):
    user = request.user
    uploads = list(PrivatePDFUpload.objects.filter(user=user))
    export_data = {
        'format_version': 1,
        'exported_at': timezone.now(),
        'entries': list(
            DashboardEntry.objects.filter(user=user).values(
                'kind', 'title', 'description', 'status', 'progress', 'target_date', 'created_at', 'updated_at',
            )
        ),
        'schedule_items': list(
            DashboardScheduleItem.objects.filter(user=user).values(
                'kind', 'title', 'description', 'date', 'weekday', 'start_time', 'end_time', 'location', 'created_at',
            )
        ),
        'quotes': list(
            DashboardQuote.objects.filter(user=user).values('text', 'author', 'is_favorite', 'created_at')
        ),
        'finance_transactions': list(
            FinanceTransaction.objects.filter(user=user).values(
                'kind', 'title', 'amount', 'currency', 'category', 'date', 'notes', 'created_at', 'updated_at',
            )
        ),
        'files': [
            {
                'archive_path': _pdf_archive_path(upload),
                'original_filename': upload.original_filename,
                'file_size': upload.file_size,
                'uploaded_at': upload.uploaded_at,
            }
            for upload in uploads
        ],
    }

    archive_buffer = SpooledTemporaryFile(max_size=10 * 1024 * 1024, mode='w+b')
    with ZipFile(archive_buffer, mode='w', compression=ZIP_DEFLATED) as archive:
        archive.writestr('data.json', json.dumps(export_data, cls=DjangoJSONEncoder, indent=2))
        for upload in uploads:
            if not upload.file or not upload.file.storage.exists(upload.file.name):
                continue
            with archive.open(_pdf_archive_path(upload), mode='w') as archived_file:
                with upload.file.open('rb') as source_file:
                    for chunk in source_file.chunks():
                        archived_file.write(chunk)

    archive_buffer.seek(0)
    filename = f'mylifehub-backup-{timezone.localdate().isoformat()}.zip'
    response = FileResponse(archive_buffer, as_attachment=True, filename=filename, content_type='application/zip')
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def add_entry(request, kind):
    valid_kinds = {choice for choice, _label in DashboardEntry.Kind.choices}
    if kind not in valid_kinds:
        messages.error(request, 'That item type is not available.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = DashboardEntryForm(request.POST, kind=kind)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.kind = kind
            if kind == DashboardEntry.Kind.GOAL and entry.status == DashboardEntry.Status.COMPLETED:
                entry.progress = 100
            entry.save()
            messages.success(request, f'{entry.get_kind_display()} saved.')
            return redirect('dashboard:index')
    else:
        form = DashboardEntryForm(kind=kind)

    title = dict(DashboardEntry.Kind.choices)[kind]
    return render(request, 'dashboard/entry_form.html', {'form': form, 'item_title': title})


@login_required
def add_schedule_item(request, kind):
    if kind not in SCHEDULE_KINDS:
        messages.error(request, 'That schedule type is not available.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = DashboardScheduleForm(request.POST, kind=kind)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.kind = kind
            item.save()
            messages.success(request, f'{item.get_kind_display()} added to your schedule.')
            return redirect('dashboard:index')
    else:
        form = DashboardScheduleForm(kind=kind)

    item_title = dict(DashboardScheduleItem.Kind.choices)[kind]
    return render(request, 'dashboard/schedule_form.html', {'form': form, 'item_title': item_title})


@login_required
def add_quote(request):
    if request.method == 'POST':
        form = DashboardQuoteForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.user = request.user
            quote.save()
            messages.success(request, 'Your quote has been saved.')
            return redirect('dashboard:index')
    else:
        form = DashboardQuoteForm()
    return render(request, 'dashboard/quote_form.html', {'form': form})
