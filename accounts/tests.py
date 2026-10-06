from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class AuthenticationFlowTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username='reader',
			email='reader@example.com',
			password='a-strong-test-password',
		)

	def test_user_can_sign_in(self):
		response = self.client.post(
			reverse('accounts:login'),
			{'username': 'reader', 'password': 'a-strong-test-password'},
		)

		self.assertRedirects(response, reverse('dashboard:index'))
		self.assertTrue(response.wsgi_request.user.is_authenticated)

	def test_sign_out_requires_post(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('accounts:logout'))
		self.assertEqual(response.status_code, 405)

		response = self.client.post(reverse('accounts:logout'))
		self.assertRedirects(response, reverse('accounts:login'))

	def test_password_reset_sends_email(self):
		response = self.client.post(
			reverse('accounts:password_reset'),
			{'email': 'reader@example.com'},
		)

		self.assertRedirects(response, reverse('accounts:password_reset_done'))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('/accounts/password-reset/confirm/', mail.outbox[0].body)
