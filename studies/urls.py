from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cadastro/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('sair/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('estudar/', views.study, name='study'),
    path('revisao/<int:state_id>/', views.review, name='review'),
]
