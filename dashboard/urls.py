from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('settings/', views.settings_view, name='settings'),
    path('search/', views.search, name='search'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('export/', views.export, name='export'),
    path('files/', views.files, name='files'),
    path('files/<int:upload_id>/download/', views.download_file, name='download_file'),
    path('files/<int:upload_id>/delete/', views.delete_file, name='delete_file'),
    path('library/', views.library_overview, name='library'),
    path('library/<str:kind>/<int:entry_id>/edit/', views.edit_entry, name='edit_entry'),
    path('library/<str:kind>/<int:entry_id>/delete/', views.delete_entry, name='delete_entry'),
    path('library/<str:kind>/', views.entries_by_kind, name='entries_by_kind'),
    path('library/<str:kind>/<int:entry_id>/', views.entry_detail, name='entry_detail'),
    path('add/<str:kind>/', views.add_entry, name='add_entry'),
    path('schedule/add/<str:kind>/', views.add_schedule_item, name='add_schedule_item'),
    path('quotes/add/', views.add_quote, name='add_quote'),
]