import json
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
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard:index'))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard:index')}")

    def test_authenticated_user_can_open_dashboard(self):
        user = get_user_model().objects.create_user(username='reader', password='a-strong-test-password')
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/index.html')
        self.assertContains(response, 'data-immersive-navigation')
        self.assertContains(response, 'data-nav-section="Learning"')
        self.assertContains(response, 'data-nav-section="Entertainment"')

    def test_settings_and_entertainment_sections_are_real_pages(self):
        user = get_user_model().objects.create_user(username='section-reader', password='a-strong-test-password')
        self.client.force_login(user)

        settings_response = self.client.get(reverse('dashboard:settings'))
        entertainment_response = self.client.get(
            reverse('dashboard:entries_by_kind', kwargs={'kind': 'entertainment'})
        )

        self.assertEqual(settings_response.status_code, 200)
        self.assertContains(settings_response, 'Settings')
        self.assertEqual(entertainment_response.status_code, 200)
        self.assertContains(entertainment_response, 'Entertainment')

    def test_anonymous_user_cannot_export_personal_data(self):
        response = self.client.get(reverse('dashboard:export'))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard:export')}")


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
        upload_response = self.client.post(reverse('dashboard:files'), {'pdf': self.make_pdf()})

        self.assertRedirects(upload_response, reverse('dashboard:files'))
        upload = PrivatePDFUpload.objects.get(original_filename='personal.pdf')
        self.assertEqual(upload.user, self.user)
        self.assertTrue(upload.file.name.startswith(f'private_uploads/{self.user.pk}/'))
        other_upload_file = self.make_pdf(name='other.pdf')
        PrivatePDFUpload.objects.create(
            user=self.other_user,
            original_filename='other.pdf',
            file=other_upload_file,
            file_size=other_upload_file.size,
        )
        library_response = self.client.get(reverse('dashboard:files'))
        self.assertContains(library_response, 'personal.pdf')
        self.assertNotContains(library_response, 'other.pdf')

        download_response = self.client.get(reverse('dashboard:download_file', kwargs={'upload_id': upload.pk}))
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(download_response.streaming_content), b'%PDF-1.7\nprivate file')
        download_response.close()

        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(reverse('dashboard:download_file', kwargs={'upload_id': upload.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('dashboard:delete_file', kwargs={'upload_id': upload.pk})).status_code, 404)
        self.assertTrue(PrivatePDFUpload.objects.filter(pk=upload.pk).exists())

    def test_upload_rejects_fake_pdf_content(self):
        response = self.client.post(
            reverse('dashboard:files'),
            {'pdf': self.make_pdf(content=b'not a PDF')},
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
