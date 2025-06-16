from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('screening/<int:screening_id>/', views.screening_detail, name='screening_detail'),
    path('book/', views.book_tickets, name='book_tickets'),
    path('download-ticket/', views.download_ticket, name='download_ticket'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/movies/', views.movie_manage, name='movie_manage'),
    path('admin/movies/add/', views.movie_add, name='movie_add'),
    path('admin/movies/edit/<int:movie_id>/', views.movie_edit, name='movie_edit'),
    path('admin/movies/delete/<int:movie_id>/', views.movie_delete, name='movie_delete'),
    path('admin/hall/', views.hall_manage, name='hall_manage'),
    path('admin/hall/add/', views.hall_add, name='hall_add'),
    path('admin/hall/edit/<int:hall_id>/', views.hall_edit, name='hall_edit'),
    path('admin/hall/delete/<int:hall_id>/', views.hall_delete, name='hall_delete'),
    path('admin/screening/', views.screening_manage, name='screening_manage'),
    path('admin/screening/add/', views.screening_add, name='screening_add'),
    path('admin/screening/edit/<int:screening_id>/', views.screening_edit, name='screening_edit'),
    path('admin/screening/delete/<int:screening_id>/', views.screening_delete, name='screening_delete'),
    path('profile/', views.profile, name='profile'),
    path('download-ticket/<int:ticket_id>/', views.download_ticket_single, name='download_ticket_single'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)