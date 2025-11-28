from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('screening/<int:screening_id>/', views.screening_detail, name='screening_detail'),
    path('screening/<int:screening_id>/partial/', views.screening_partial, name='screening_partial'),
    path('book/', views.book_tickets, name='book_tickets'),
    path('download-ticket/', views.download_ticket, name='download_ticket'),
    # Админка
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
    path('download-ticket-group/<str:group_id>/', views.download_ticket_group, name='download_ticket_group'),
    # Почта
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification-code/', views.resend_verification_code, name='resend_verification_code'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/code/', views.password_reset_code, name='password_reset_code'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    # Руководство пользователя
    path('about/', views.about, name='about'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)