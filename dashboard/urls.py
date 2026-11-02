from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    # Public landing page — the developer portfolio, readable without signing in.
    path('', views.portfolio, name='portfolio'),
    path('dashboard/', views.index, name='index'),
    path('settings/', views.settings_view, name='settings'),
    path('search/', views.search, name='search'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('diary/', views.diary_workspace, name='diary'),
    path('projects/', views.projects_workspace, name='projects'),
    path('export/', views.export, name='export'),
    path('files/', views.files, name='files'),
    path('files/<int:upload_id>/download/', views.download_file, name='download_file'),
    path('files/<int:upload_id>/preview/', views.preview_file, name='preview_file'),
    path('files/<int:upload_id>/delete/', views.delete_file, name='delete_file'),
    path('learning/', views.learning_library, name='learning'),
    path('learning/pdfs/', views.pdf_library, name='pdfs'),
    path('learning/add/', views.add_resource, name='add_resource'),
    path('learning/<int:upload_id>/', views.resource_detail, name='resource_detail'),
    path('learning/<int:upload_id>/edit/', views.edit_resource, name='edit_resource'),
    path('learning/assignments/', views.assignments, name='assignments'),
    path('learning/assignments/add/', views.add_assignment, name='add_assignment'),
    path('learning/assignments/<int:assignment_id>/edit/', views.edit_assignment, name='edit_assignment'),
    path('learning/assignments/<int:assignment_id>/delete/', views.delete_assignment, name='delete_assignment'),
    path('library/', views.library_overview, name='library'),
    # Study notebooks live in the Library, separate from life-archive meeting notes.
    path('notebooks/', views.notebook_list, name='notebooks'),
    path('notebooks/add/', views.add_notebook, name='add_notebook'),
    path('notebooks/<int:notebook_id>/', views.notebook_detail, name='notebook_detail'),
    path('notebooks/<int:notebook_id>/edit/', views.edit_notebook, name='edit_notebook'),
    path('notebooks/<int:notebook_id>/delete/', views.delete_notebook, name='delete_notebook'),
    path('notebooks/<int:notebook_id>/pin/', views.toggle_notebook_pin, name='toggle_notebook_pin'),
    path('notebooks/<int:notebook_id>/pages/add/', views.add_study_note, name='add_study_note'),
    path('notebooks/<int:notebook_id>/pages/<int:note_id>/', views.study_note_detail, name='study_note_detail'),
    path('notebooks/<int:notebook_id>/pages/<int:note_id>/edit/', views.edit_study_note, name='edit_study_note'),
    path('notebooks/<int:notebook_id>/pages/<int:note_id>/delete/', views.delete_study_note, name='delete_study_note'),
    path('notebooks/<int:notebook_id>/pages/<int:note_id>/pin/', views.toggle_study_note_pin, name='toggle_study_note_pin'),
    path('library/<str:kind>/<int:entry_id>/edit/', views.edit_entry, name='edit_entry'),
    path('library/<str:kind>/<int:entry_id>/delete/', views.delete_entry, name='delete_entry'),
    path('library/<str:kind>/<int:entry_id>/pin/', views.toggle_pin, name='toggle_pin'),
    path('library/<str:kind>/', views.entries_by_kind, name='entries_by_kind'),
    path('library/<str:kind>/<int:entry_id>/', views.entry_detail, name='entry_detail'),
    path('add/<str:kind>/', views.add_entry, name='add_entry'),
    path('schedule/add/<str:kind>/', views.add_schedule_item, name='add_schedule_item'),
    path('quotes/add/', views.add_quote, name='add_quote'),
    path('quotes/random/', views.random_quote, name='random_quote'),
]