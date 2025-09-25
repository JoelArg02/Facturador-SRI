from django.urls import path
from core.subscription.views.plan import (
    PlanListView, PlanCreateView, PlanUpdateView, PlanDeleteView
)
from core.subscription.views.subscription import (
    SubscriptionListView, SubscriptionCreateView, SubscriptionUpdateView, SubscriptionDeleteView,
    SubscriptionRequiredView, SubscriptionLogoutView,
)

urlpatterns = [
    path('plan/', PlanListView.as_view(), name='plan_list'),
    path('plan/create/', PlanCreateView.as_view(), name='plan_create'),
    path('plan/update/<int:pk>/', PlanUpdateView.as_view(), name='plan_update'),
    path('plan/delete/<int:pk>/', PlanDeleteView.as_view(), name='plan_delete'),

    path('', SubscriptionListView.as_view(), name='subscription_list'),
    path('create/', SubscriptionCreateView.as_view(), name='subscription_create'),
    path('update/<int:pk>/', SubscriptionUpdateView.as_view(), name='subscription_update'),
    path('delete/<int:pk>/', SubscriptionDeleteView.as_view(), name='subscription_delete'),
    path('required/', SubscriptionRequiredView.as_view(), name='subscription_required'),
    path('logout/', SubscriptionLogoutView.as_view(), name='subscription_logout'),
]
