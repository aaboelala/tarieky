from django.urls import path
from .views import (
    IssueListCreateView,
    IssueDetailView,
    NearbyIssuesView,
    IssueStatusUpdateView,
    UserProfileView,
    NotificationListView,
    NotificationReadView,
    MyIssuesListView,
    UserIssueStatsView,
    RegisterDeviceTokenView,
)

urlpatterns = [
    path('issues/', IssueListCreateView.as_view(), name='issue-list-create'),
    path('issues/my/', MyIssuesListView.as_view(), name='my-issues'),
    path('issues/my/stats/', UserIssueStatsView.as_view(), name='my-issues-stats'),
    path('issues/nearby/', NearbyIssuesView.as_view(), name='issues-nearby'),
    path('issues/<int:pk>/', IssueDetailView.as_view(), name='issue-detail'),
    path('issues/<int:pk>/status/', IssueStatusUpdateView.as_view(), name='issue-status-update'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification-read'),
    path('device-token/', RegisterDeviceTokenView.as_view(), name='register-device-token'),
]
