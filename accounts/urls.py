from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

app_name = 'accounts'


@require_http_methods(['GET', 'POST'])
def portfolio_login_redirect(request):
    """Send sign-in traffic to the public portfolio.

    GET renders the portfolio with the credential modal already open. A POST
    still authenticates through Django's LoginView so the standalone URL keeps
    working for anything that posts to it directly.

    A plain visit to this URL (no ?next=) is treated as a fresh arrival: the
    visitor is sent to the clean portfolio gate so that leaving the page and
    coming back always returns them to the first page they were meant to sign
    in at, instead of a stale deep link.
    """
    if request.method == 'POST':
        return auth_views.LoginView.as_view()(request)

    portfolio_url = reverse_lazy('dashboard:portfolio')
    next_url = request.GET.get('next', '')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = ''
    if request.user.is_authenticated:
        return redirect(next_url or reverse_lazy('dashboard:index'))
    if next_url:
        return redirect(f"{portfolio_url}?next={next_url}")
    return redirect(portfolio_url)


def portfolio_logout_redirect(request):
    """Sign the visitor out and return them to the clean portfolio gate.

    Django's default LogoutView lands on a bare logged-out page. Sending the
    visitor back to the portfolio instead means the next thing they see is the
    same sign-in entry point they started from.
    """
    return auth_views.LogoutView.as_view(
        next_page=reverse_lazy('dashboard:portfolio')
    )(request)

urlpatterns = [
    # Signing in happens in the modal on the public portfolio, so the standalone
    # login URL forwards there with ?next= preserved — the visitor sees the
    # portfolio with the credential form already open, and returns to the page
    # they originally wanted afterwards.
    path('login/', portfolio_login_redirect, name='login'),
    path('logout/', portfolio_logout_redirect, name='logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
        name='password_reset_complete',
    ),
]