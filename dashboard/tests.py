import json
from datetime import date
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from finance.models import FinanceTransaction

from .models import DashboardEntry, DashboardQuote, DashboardScheduleItem, PrivatePDFUpload


class DashboardAccessTests(TestCase):
    def test_portfolio_landing_page_is_public(self):
        response = self.client.get(reverse('dashboard:portfolio'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/portfolio.html')
        self.assertContains(response, 'data-login-overlay')

    def test_private_pages_bounce_anonymous_users_back_to_portfolio_login(self):
        """A signed-out visitor lands on the portfolio with the login modal primed."""
        response = self.client.get(reverse('dashboard:index'))

        # First hop: Django's login_required sends us to the login URL.
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('dashboard:index')}",
            fetch_redirect_response=False,
        )
        # Second hop: the login URL forwards to the portfolio carrying ?next=,
        # so the credential modal opens and the destination is remembered.
        follow = self.client.get(response['Location'])
        self.assertRedirects(
            follow,
            f"{reverse('dashboard:portfolio')}?next={reverse('dashboard:index')}",
        )
        landing = self.client.get(f"{reverse('dashboard:portfolio')}?next={reverse('dashboard:index')}")
        self.assertEqual(landing.status_code, 200)
        self.assertTrue(landing.context['open_login'])

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard:index'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('dashboard:index')}",
            fetch_redirect_response=False,
        )

    def test_authenticated_user_can_open_dashboard(self):
        user = get_user_model().objects.create_user(username='reader', password='a-strong-test-password')
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')
        self.assertContains(response, 'data-immersive-navigation')
        self.assertContains(response, 'data-nav-section="Learning"')
        self.assertContains(response, 'data-nav-section="Diary"')
        self.assertNotContains(response, 'data-nav-section="Entertainment"')

    def test_settings_and_diary_sections_are_real_pages(self):
        user = get_user_model().objects.create_user(username='section-reader', password='a-strong-test-password')
        self.client.force_login(user)

        settings_response = self.client.get(reverse('dashboard:settings'))
        diary_response = self.client.get(reverse('dashboard:diary'))
        learning_response = self.client.get(reverse('dashboard:learning'))

        self.assertEqual(settings_response.status_code, 200)
        self.assertContains(settings_response, 'Settings')
        self.assertEqual(diary_response.status_code, 200)
        self.assertContains(diary_response, 'diary')
        self.assertEqual(learning_response.status_code, 200)
        self.assertContains(learning_response, 'Learning library')

    def test_anonymous_user_cannot_export_personal_data(self):
        response = self.client.get(reverse('dashboard:export'))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('dashboard:export')}",
            fetch_redirect_response=False,
        )


class DashboardDataTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='owner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='other', password='a-strong-test-password')
        self.client.force_login(self.user)

    def test_dashboard_counts_only_the_signed_in_users_entries(self):
        DashboardEntry.objects.create(user=self.user, kind=DashboardEntry.Kind.NOTE, title='My note')
        DashboardEntry.objects.create(user=self.other_user, kind=DashboardEntry.Kind.NOTE, title='Private note')

        response = self.client.get(reverse('dashboard:index'))

        notes = next(stat for stat in response.context['stats'] if stat['label'] == 'Notes')
        self.assertEqual(notes['count'], 1)
        self.assertContains(response, 'My note')
        self.assertNotContains(response, 'Private note')

    def test_quick_capture_creates_a_private_note(self):
        response = self.client.post(
            reverse('dashboard:add_entry', kwargs={'kind': DashboardEntry.Kind.NOTE}),
            {'title': 'A thought', 'description': 'Keep this for later.'},
        )

        self.assertRedirects(response, reverse('dashboard:index'))
        entry = DashboardEntry.objects.get(title='A thought')
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.kind, DashboardEntry.Kind.NOTE)

    def test_saved_quote_is_shown_on_dashboard(self):
        DashboardQuote.objects.create(user=self.user, text='Keep going.', author='A friend')

        response = self.client.get(reverse('dashboard:index'))

        self.assertContains(response, 'Keep going.')
        self.assertContains(response, 'A friend')

    def test_timetable_and_upcoming_events_are_user_scoped(self):
        from django.utils import timezone

        today = timezone.localdate()
        DashboardScheduleItem.objects.create(
            user=self.user,
            kind=DashboardScheduleItem.Kind.TIMETABLE,
            title='Study session',
            weekday=today.weekday(),
        )
        DashboardScheduleItem.objects.create(
            user=self.other_user,
            kind=DashboardScheduleItem.Kind.EVENT,
            title='Private event',
            date=today,
        )

        response = self.client.get(reverse('dashboard:index'))

        self.assertContains(response, 'Study session')
        self.assertNotContains(response, 'Private event')

    def test_schedule_rejects_end_time_before_start_time(self):
        from django.utils import timezone

        response = self.client.post(
            reverse('dashboard:add_schedule_item', kwargs={'kind': DashboardScheduleItem.Kind.EVENT}),
            {
                'title': 'Meeting',
                'date': timezone.localdate().isoformat(),
                'start_time': '15:00',
                'end_time': '14:00',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DashboardScheduleItem.objects.filter(title='Meeting').exists())
        self.assertContains(response, 'End time must be later than start time.')

    def test_library_overview_lists_user_life_collections(self):
        DashboardEntry.objects.create(user=self.user, kind=DashboardEntry.Kind.NOTE, title='My note for the archive')

        response = self.client.get(reverse('dashboard:library'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your life archive')
        self.assertContains(response, 'Notes')
        self.assertContains(response, 'My note for the archive')

    def test_entries_by_kind_only_returns_the_signed_in_users_records(self):
        DashboardEntry.objects.create(user=self.user, kind=DashboardEntry.Kind.GOAL, title='Finish my deep work block')
        DashboardEntry.objects.create(user=self.other_user, kind=DashboardEntry.Kind.GOAL, title='Other user goal')

        response = self.client.get(reverse('dashboard:entries_by_kind', kwargs={'kind': DashboardEntry.Kind.GOAL}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Finish my deep work block')
        self.assertNotContains(response, 'Other user goal')

    def test_global_search_returns_user_scoped_results_across_module_types(self):
        DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.NOTE,
            title='Weekend planning',
            description='Need a calmer plan for the weekend retreat.',
        )
        DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.GOAL,
            title='Finish the portfolio refresh',
            description='Refresh the personal portfolio and priorities.',
        )
        DashboardEntry.objects.create(
            user=self.other_user,
            kind=DashboardEntry.Kind.NOTE,
            title='Weekend planning',
            description='Private plan for the other user.',
        )
        FinanceTransaction.objects.create(
            user=self.user,
            kind=FinanceTransaction.Kind.EXPENSE,
            title='Weekend transit expense',
            amount='18.00',
        )
        FinanceTransaction.objects.create(
            user=self.other_user,
            kind=FinanceTransaction.Kind.EXPENSE,
            title='Private weekend expense',
            amount='90.00',
        )

        response = self.client.get(reverse('dashboard:search'), {'q': 'weekend'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Weekend planning')
        self.assertContains(response, 'Weekend transit expense')
        self.assertNotContains(response, 'Private plan for the other user.')
        self.assertNotContains(response, 'Private weekend expense')

    def test_calendar_shows_only_owned_items_in_the_requested_month(self):
        DashboardScheduleItem.objects.create(
            user=self.user,
            kind=DashboardScheduleItem.Kind.EVENT,
            title='October appointment',
            date='2026-10-12',
        )
        DashboardScheduleItem.objects.create(
            user=self.other_user,
            kind=DashboardScheduleItem.Kind.EVENT,
            title='Private appointment',
            date='2026-10-12',
        )
        DashboardScheduleItem.objects.create(
            user=self.user,
            kind=DashboardScheduleItem.Kind.DEADLINE,
            title='November deadline',
            date='2026-11-02',
        )

        response = self.client.get(reverse('dashboard:calendar'), {'year': 2026, 'month': 10})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'October appointment')
        self.assertNotContains(response, 'Private appointment')
        self.assertNotContains(response, 'November deadline')
        self.assertContains(response, 'October 2026')

    def test_owner_can_edit_a_life_entry(self):
        entry = DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.NOTE,
            title='Draft thought',
            description='Old details',
        )

        response = self.client.post(
            reverse('dashboard:edit_entry', kwargs={'kind': entry.kind, 'entry_id': entry.pk}),
            {'title': 'Updated thought', 'description': 'New details'},
        )

        self.assertRedirects(
            response,
            reverse('dashboard:entry_detail', kwargs={'kind': entry.kind, 'entry_id': entry.pk}),
        )
        entry.refresh_from_db()
        self.assertEqual(entry.title, 'Updated thought')
        self.assertEqual(entry.description, 'New details')

    def test_owner_can_delete_a_life_entry_with_post(self):
        entry = DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.NOTE,
            title='Remove this note',
        )
        delete_url = reverse('dashboard:delete_entry', kwargs={'kind': entry.kind, 'entry_id': entry.pk})

        confirm_response = self.client.get(delete_url)
        delete_response = self.client.post(delete_url)

        self.assertEqual(confirm_response.status_code, 200)
        self.assertRedirects(delete_response, reverse('dashboard:entries_by_kind', kwargs={'kind': entry.kind}))
        self.assertFalse(DashboardEntry.objects.filter(pk=entry.pk).exists())

    def test_user_cannot_edit_or_delete_another_users_life_entry(self):
        entry = DashboardEntry.objects.create(
            user=self.other_user,
            kind=DashboardEntry.Kind.NOTE,
            title='Private note',
        )
        edit_url = reverse('dashboard:edit_entry', kwargs={'kind': entry.kind, 'entry_id': entry.pk})
        delete_url = reverse('dashboard:delete_entry', kwargs={'kind': entry.kind, 'entry_id': entry.pk})

        self.assertEqual(self.client.get(edit_url).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.assertTrue(DashboardEntry.objects.filter(pk=entry.pk).exists())


class PrivatePDFTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='file-owner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='file-other', password='a-strong-test-password')
        self.client.force_login(self.user)
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(self.media_dir.cleanup)
        self.addCleanup(media_settings.disable)

    def make_pdf(self, name='personal.pdf', content=b'%PDF-1.7\nprivate file'):
        return SimpleUploadedFile(name, content, content_type='application/pdf')

    def test_pdf_upload_and_download_are_private_to_the_owner(self):
        upload_response = self.client.post(
            reverse('dashboard:add_resource'),
            {'title': 'Personal PDF', 'category': 'other', 'file': self.make_pdf()},
        )

        self.assertRedirects(upload_response, reverse('dashboard:learning'))
        upload = PrivatePDFUpload.objects.get(original_filename='personal.pdf')
        self.assertEqual(upload.user, self.user)
        self.assertTrue(upload.file.name.startswith(f'private_uploads/{self.user.pk}/'))
        other_upload_file = self.make_pdf(name='other.pdf')
        PrivatePDFUpload.objects.create(
            user=self.other_user,
            original_filename='other.pdf',
            title='Other file',
            file=other_upload_file,
            file_size=other_upload_file.size,
        )
        library_response = self.client.get(reverse('dashboard:learning'))
        self.assertContains(library_response, 'Personal PDF')
        self.assertNotContains(library_response, 'Other file')

        download_response = self.client.get(reverse('dashboard:download_file', kwargs={'upload_id': upload.pk}))
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(download_response.streaming_content), b'%PDF-1.7\nprivate file')
        download_response.close()

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(reverse('dashboard:download_file', kwargs={'upload_id': upload.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('dashboard:delete_file', kwargs={'upload_id': upload.pk})).status_code, 404)
        self.assertTrue(PrivatePDFUpload.objects.filter(pk=upload.pk).exists())

    def test_legacy_files_url_redirects_to_learning(self):
        response = self.client.get(reverse('dashboard:files'))
        self.assertRedirects(response, reverse('dashboard:learning'))

    def test_upload_rejects_fake_pdf_content(self):
        response = self.client.post(
            reverse('dashboard:add_resource'),
            {'title': 'Fake', 'category': 'other', 'file': self.make_pdf(content=b'not a PDF')},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This file does not have a valid PDF signature.')
        self.assertFalse(PrivatePDFUpload.objects.exists())


class PersonalExportTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='export-owner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='export-other', password='a-strong-test-password')
        self.client.force_login(self.user)
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(self.media_dir.cleanup)
        self.addCleanup(media_settings.disable)

    def test_zip_export_contains_only_owned_data_and_private_pdf(self):
        DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.NOTE,
            title='My exported note',
            description='Private details',
        )
        DashboardEntry.objects.create(
            user=self.other_user,
            kind=DashboardEntry.Kind.NOTE,
            title='Another user note',
        )
        FinanceTransaction.objects.create(
            user=self.user,
            kind=FinanceTransaction.Kind.EXPENSE,
            title='Exported expense',
            amount='12.50',
            currency=FinanceTransaction.Currency.USD,
        )
        uploaded_file = SimpleUploadedFile('export.pdf', b'%PDF-1.7\nbackup file', content_type='application/pdf')
        private_upload = PrivatePDFUpload.objects.create(
            user=self.user,
            original_filename='export.pdf',
            file=uploaded_file,
            file_size=uploaded_file.size,
        )

        response = self.client.get(reverse('dashboard:export'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertIn('private, no-store', response['Cache-Control'])
        archive_bytes = b''.join(response.streaming_content)
        response.close()
        with ZipFile(BytesIO(archive_bytes)) as archive:
            data_bytes = archive.read('data.json')
            data = json.loads(data_bytes)
            self.assertEqual([entry['title'] for entry in data['entries']], ['My exported note'])
            self.assertEqual([item['title'] for item in data['finance_transactions']], ['Exported expense'])
            archive_path = f'files/{private_upload.pk}-export.pdf'
            self.assertEqual(data['files'][0]['archive_path'], archive_path)
            self.assertEqual(archive.read(archive_path), b'%PDF-1.7\nbackup file')
            self.assertNotIn(b'Another user note', data_bytes)



class DiaryWorkspaceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='diary-owner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='diary-other', password='a-strong-test-password')
        self.client.force_login(self.user)

    def test_diary_workspace_renders_with_stats_and_calendar(self):
        DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.DIARY,
            title='A good day',
            description='Today was productive.',
            mood=DashboardEntry.Mood.GREAT,
        )
        response = self.client.get(reverse('dashboard:diary'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A good day')
        self.assertContains(response, 'Day writing streak')
        self.assertContains(response, 'Writing calendar')

    def test_diary_entries_are_private_to_the_owner(self):
        DashboardEntry.objects.create(
            user=self.other_user,
            kind=DashboardEntry.Kind.DIARY,
            title='Someone else entry',
        )
        response = self.client.get(reverse('dashboard:diary'))
        self.assertNotContains(response, 'Someone else entry')

    def test_diary_entry_saves_mood_and_persists(self):
        response = self.client.post(
            reverse('dashboard:add_entry', kwargs={'kind': DashboardEntry.Kind.DIARY}),
            {'title': 'Moody day', 'description': 'Felt calm.', 'mood': 'good'},
        )
        self.assertRedirects(response, reverse('dashboard:index'))
        entry = DashboardEntry.objects.get(title='Moody day')
        self.assertEqual(entry.mood, 'good')
        self.assertEqual(entry.kind, DashboardEntry.Kind.DIARY)

    def test_pin_toggle_persists(self):
        entry = DashboardEntry.objects.create(
            user=self.user,
            kind=DashboardEntry.Kind.DIARY,
            title='Pin me',
        )
        self.assertFalse(entry.is_pinned)
        self.client.post(reverse('dashboard:toggle_pin', kwargs={'kind': entry.kind, 'entry_id': entry.pk}))
        entry.refresh_from_db()
        self.assertTrue(entry.is_pinned)
        self.client.post(reverse('dashboard:toggle_pin', kwargs={'kind': entry.kind, 'entry_id': entry.pk}))
        entry.refresh_from_db()
        self.assertFalse(entry.is_pinned)

    def test_user_cannot_pin_another_users_entry(self):
        entry = DashboardEntry.objects.create(
            user=self.other_user,
            kind=DashboardEntry.Kind.DIARY,
            title='Not yours',
        )
        response = self.client.post(
            reverse('dashboard:toggle_pin', kwargs={'kind': entry.kind, 'entry_id': entry.pk})
        )
        self.assertEqual(response.status_code, 404)
        entry.refresh_from_db()
        self.assertFalse(entry.is_pinned)


class LearningLibraryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='learner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='learner-other', password='a-strong-test-password')
        self.client.force_login(self.user)
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(self.media_dir.cleanup)
        self.addCleanup(media_settings.disable)

    def make_pdf(self, name='notes.pdf', content=b'%PDF-1.7\nlearning material'):
        return SimpleUploadedFile(name, content, content_type='application/pdf')

    def test_learning_library_renders(self):
        response = self.client.get(reverse('dashboard:learning'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Learning library')

    def test_upload_resource_persists_with_metadata(self):
        response = self.client.post(
            reverse('dashboard:add_resource'),
            {
                'title': 'Data Structures Notes',
                'category': 'lecture',
                'notes': 'Week 1 to 4',
                'file': self.make_pdf(),
            },
        )
        self.assertRedirects(response, reverse('dashboard:learning'))
        resource = PrivatePDFUpload.objects.get(title='Data Structures Notes')
        self.assertEqual(resource.user, self.user)
        self.assertEqual(resource.category, 'lecture')
        self.assertEqual(resource.original_filename, 'notes.pdf')
        self.assertEqual(resource.notes, 'Week 1 to 4')

    def test_resources_are_private_to_the_owner(self):
        PrivatePDFUpload.objects.create(
            user=self.other_user,
            original_filename='private.pdf',
            title='Other user material',
            file=self.make_pdf('private.pdf'),
            file_size=30,
        )
        response = self.client.get(reverse('dashboard:learning'))
        self.assertNotContains(response, 'Other user material')

    def test_category_filter_works(self):
        PrivatePDFUpload.objects.create(
            user=self.user,
            original_filename='slides.pdf',
            title='Chapter Slides',
            category='slides',
            file=self.make_pdf('slides.pdf'),
            file_size=30,
        )
        response = self.client.get(reverse('dashboard:learning'), {'category': 'slides'})
        self.assertContains(response, 'Chapter Slides')
        response = self.client.get(reverse('dashboard:learning'), {'category': 'exam'})
        self.assertNotContains(response, 'Chapter Slides')

    def test_resource_detail_is_user_scoped(self):
        resource = PrivatePDFUpload.objects.create(
            user=self.other_user,
            original_filename='secret.pdf',
            title='Secret material',
            file=self.make_pdf('secret.pdf'),
            file_size=30,
        )
        response = self.client.get(reverse('dashboard:resource_detail', kwargs={'upload_id': resource.pk}))
        self.assertEqual(response.status_code, 404)

    def test_non_pdf_upload_is_rejected(self):
        bad_file = SimpleUploadedFile('notes.txt', b'just text', content_type='text/plain')
        response = self.client.post(
            reverse('dashboard:add_resource'),
            {'title': 'Bad file', 'category': 'other', 'file': bad_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PrivatePDFUpload.objects.filter(title='Bad file').exists())


class QuoteRotationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='quote-owner', password='a-strong-test-password')
        self.client.force_login(self.user)

    def test_quote_of_the_day_is_deterministic_per_day(self):
        DashboardQuote.objects.create(user=self.user, text='First quote')
        DashboardQuote.objects.create(user=self.user, text='Second quote')
        first = self.client.get(reverse('dashboard:index')).context['quote_of_day']
        second = self.client.get(reverse('dashboard:index')).context['quote_of_day']
        self.assertEqual(first.pk, second.pk)

    def test_favorite_quotes_are_preferred(self):
        DashboardQuote.objects.create(user=self.user, text='Normal quote')
        favorite = DashboardQuote.objects.create(user=self.user, text='Favorite quote', is_favorite=True)
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.context['quote_of_day'].pk, favorite.pk)



class ProjectsWorkspaceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='project-owner', password='a-strong-test-password')
        self.other_user = user_model.objects.create_user(username='project-other', password='a-strong-test-password')
        self.client.force_login(self.user)

    def make_project(self, **overrides):
        data = {
            'title': 'Campus Ride Share',
            'description': 'A ride-sharing platform for students.',
            'client': 'Innovation Hub',
            'role': 'Lead Developer',
            'status': DashboardEntry.Status.IN_PROGRESS,
            'priority': DashboardEntry.Priority.HIGH,
            'progress': 65,
            'period_start': '2026-01-15',
            'period_end': '2026-06-30',
            'tech_stack': 'Django, Python, PostgreSQL',
            'repo_url': 'https://github.com/example/repo',
        }
        data.update(overrides)
        return DashboardEntry.objects.create(user=self.user, kind=DashboardEntry.Kind.PROJECT, **data)

    def test_projects_workspace_renders(self):
        response = self.client.get(reverse('dashboard:projects'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total projects')

    def test_project_saves_all_fields(self):
        response = self.client.post(
            reverse('dashboard:add_entry', kwargs={'kind': DashboardEntry.Kind.PROJECT}),
            {
                'title': 'Portfolio Rewrite',
                'description': 'Rebuild the site.',
                'client': 'Personal',
                'role': 'Solo Developer',
                'status': DashboardEntry.Status.NEW,
                'priority': DashboardEntry.Priority.MEDIUM,
                'progress': 10,
                'period_start': '2026-02-01',
                'period_end': '2026-03-01',
                'tech_stack': 'Django, HTMX',
                'repo_url': 'https://github.com/example/site',
            },
        )
        self.assertRedirects(response, reverse('dashboard:index'))
        project = DashboardEntry.objects.get(title='Portfolio Rewrite')
        self.assertEqual(project.role, 'Solo Developer')
        self.assertEqual(project.client, 'Personal')
        self.assertEqual(project.priority, DashboardEntry.Priority.MEDIUM)
        self.assertEqual(project.progress, 10)
        self.assertEqual(project.tech_list, ['Django', 'HTMX'])
        self.assertEqual(project.period_label, 'Feb 2026 – Mar 2026')
        self.assertEqual(project.duration_label, '1 month')

    def test_period_label_shows_present_when_no_end_date(self):
        project = self.make_project(period_end=None)
        self.assertIn('Present', project.period_label)

    def test_duration_runs_to_today_when_still_active(self):
        # A live project with no end date measures its duration up to today.
        project = self.make_project(period_start=date(2026, 1, 15), period_end=None)
        self.assertTrue(
            project.duration_label.endswith('month') or project.duration_label.endswith('months'),
            f'unexpected duration label: {project.duration_label!r}',
        )

    def test_project_detail_page_shows_fields(self):
        project = self.make_project()
        response = self.client.get(
            reverse('dashboard:entry_detail', kwargs={'kind': project.kind, 'entry_id': project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lead Developer')
        self.assertContains(response, 'Innovation Hub')
        self.assertContains(response, 'Django')
        self.assertContains(response, 'Repository')

    def test_project_board_is_user_scoped(self):
        self.make_project()
        DashboardEntry.objects.create(
            user=self.other_user,
            kind=DashboardEntry.Kind.PROJECT,
            title='Someone else project',
        )
        response = self.client.get(reverse('dashboard:projects'))
        self.assertContains(response, 'Campus Ride Share')
        self.assertNotContains(response, 'Someone else project')

    def test_project_filters(self):
        self.make_project()
        self.make_project(title='Done Project', status=DashboardEntry.Status.COMPLETED, priority='')

        in_progress = self.client.get(reverse('dashboard:projects'), {'status': DashboardEntry.Status.IN_PROGRESS})
        self.assertContains(in_progress, 'Campus Ride Share')
        self.assertNotContains(in_progress, 'Done Project')

        completed = self.client.get(reverse('dashboard:projects'), {'status': DashboardEntry.Status.COMPLETED})
        self.assertContains(completed, 'Done Project')
        self.assertNotContains(completed, 'Campus Ride Share')

        high = self.client.get(reverse('dashboard:projects'), {'priority': DashboardEntry.Priority.HIGH})
        self.assertContains(high, 'Campus Ride Share')
        self.assertNotContains(high, 'Done Project')

        stack = self.client.get(reverse('dashboard:projects'), {'q': 'PostgreSQL'})
        self.assertContains(stack, 'Campus Ride Share')

    def test_project_stats_are_computed(self):
        self.make_project()
        self.make_project(title='Finished', status=DashboardEntry.Status.COMPLETED, progress=100)
        response = self.client.get(reverse('dashboard:projects'))
        self.assertEqual(response.context['total'], 2)
        self.assertEqual(response.context['active'], 1)
        self.assertEqual(response.context['completed'], 1)
        self.assertEqual(response.context['avg_progress'], 83)
    def test_period_end_before_start_is_rejected(self):
        response = self.client.post(
            reverse('dashboard:add_entry', kwargs={'kind': DashboardEntry.Kind.PROJECT}),
            {
                'title': 'Bad Dates',
                'description': 'x',
                'status': DashboardEntry.Status.NEW,
                'progress': 0,
                'period_start': '2026-06-01',
                'period_end': '2026-01-01',
                'tech_stack': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DashboardEntry.objects.filter(title='Bad Dates').exists())

    def test_popular_tech_is_aggregated(self):
        self.make_project()
        self.make_project(title='Second', tech_stack='Django, Docker')
        response = self.client.get(reverse('dashboard:projects'))
        tech = dict(response.context['popular_tech'])
        self.assertEqual(tech['Django'], 2)
        self.assertEqual(tech['Docker'], 1)

    def test_notes_do_not_receive_project_fields(self):
        self.client.post(
            reverse('dashboard:add_entry', kwargs={'kind': DashboardEntry.Kind.NOTE}),
            {'title': 'Just a note', 'description': 'Plain'},
        )
        note = DashboardEntry.objects.get(title='Just a note')
        self.assertEqual(note.role, '')
        self.assertEqual(note.tech_stack, '')
        self.assertEqual(note.priority, '')
