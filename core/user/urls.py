from django.urls import path
from .views.user.views import *
from .views.company import MyCompanyEditView

urlpatterns = [
    path('', UserListView.as_view(), name='user_list'),
    path('add/', UserCreateView.as_view(), name='user_create'),
    path('update/<int:pk>/', UserUpdateView.as_view(), name='user_update'),
    path('delete/<int:pk>/', UserDeleteView.as_view(), name='user_delete'),
    path('update/password/', UserUpdatePasswordView.as_view(), name='user_update_password'),
    path('update/profile/', UserUpdateProfileView.as_view(), name='user_update_profile'),
    path('choose/profile/<int:pk>/', UserChooseProfileView.as_view(), name='user_choose_profile'),
    path('ui/toggle-layout/', toggle_layout, name='ui_toggle_layout'),
    # Nueva ruta independiente para editar/crear mi empresa
    path('mi-empresa/', MyCompanyEditView.as_view(), name='my_company_edit'),
]
