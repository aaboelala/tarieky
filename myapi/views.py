import math

from django.db.models import Count, Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Issue, Notification
from .serializers import (
    IssueListSerializer,
    IssueDetailSerializer,
    IssueCreateSerializer,
    IssueStatusUpdateSerializer,
    NotificationSerializer,
    UserProfileUpdateSerializer,
    DeviceTokenSerializer,
)


# ---------- helpers ----------

def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in metres between two GPS points."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------- permissions ----------

class IsSupervisor(permissions.BasePermission):
    """Allow only verified supervisors."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'supervisor')


# ---------- views ----------

class IssueListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/issues/               → list all issues (public)
    GET  /api/issues/?city=…&governorate=…  → filtered
    POST /api/issues/               → create (authenticated, mobile)
    """

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return IssueCreateSerializer
       
        return IssueListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Issue.objects.select_related('reporter').all()
        city = self.request.query_params.get('city', '').strip()
        governorate = self.request.query_params.get('governorate', '').strip()
        status_filter = self.request.query_params.get('status', '').strip()
        
        is_supervisor = self.request.user.is_authenticated and hasattr(self.request.user, 'supervisor')
        
        if is_supervisor:
            # Supervisors can filter by status if they want
            if status_filter:
                qs = qs.filter(status=status_filter)
        else:
            # Citizens and unauthenticated users ONLY EVER see 'In Progress' issues
            qs = qs.filter(status='In Progress')
            
        if city:
            qs = qs.filter(city__icontains=city)
        if governorate:
            qs = qs.filter(governorate__icontains=governorate)
            
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(reporter=self.request.user)
        # Notify others in the city about the new issue
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users_in_city = User.objects.filter(city__iexact=instance.city).exclude(id=self.request.user.id)
        
        notifications = [
            Notification(
                user=user,
                issue=instance,
                notification_type='city_alert',
                message=f"بلاغ مروري جديد في {instance.city}: {instance.description[:50]}..."
            ) for user in users_in_city
        ]
        Notification.objects.bulk_create(notifications)


class IssueDetailView(generics.RetrieveAPIView):
    """GET /api/issues/<id>/  → single issue detail (public)."""
    queryset = Issue.objects.select_related('reporter').all()
    serializer_class = IssueDetailSerializer
    permission_classes = [permissions.AllowAny]


class MyIssuesListView(generics.ListAPIView):
    """GET /api/issues/my/  → list issues reported by the current user."""
    serializer_class = IssueListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Issue.objects.filter(
            reporter=self.request.user
        ).order_by('-created_at')


class NearbyIssuesView(APIView):
    """
    GET /api/issues/nearby/?lat=…&lon=…&radius=100
    Returns issues within `radius` metres (default 100).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params['lat'])
            lon = float(request.query_params['lon'])
        except (KeyError, ValueError):
            return Response(
                {'error': 'lat and lon query parameters are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = float(request.query_params.get('radius', 100))

        # Rough bounding box to reduce DB scan (~0.001° ≈ 111 m)
        delta = radius / 111_000
        issues = Issue.objects.select_related('reporter').filter(
            latitude__range=(lat - delta, lat + delta),
            longitude__range=(lon - delta, lon + delta),
            status='In Progress'
        )

        nearby = []
        for issue in issues:
            dist = haversine_distance(lat, lon, issue.latitude, issue.longitude)
            if dist <= radius:
                data = IssueListSerializer(issue, context={'request': request}).data
                data['distance_m'] = round(dist, 1)
                nearby.append(data)

        nearby.sort(key=lambda x: x['distance_m'])
        return Response(nearby)


class IssueStatusUpdateView(generics.UpdateAPIView):
    """PATCH /api/issues/<id>/status/  → supervisor updates status."""
    queryset = Issue.objects.all()
    serializer_class = IssueStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupervisor]

    def perform_update(self, serializer):
        instance = serializer.save()
        
        status_ar_map = {
            'Pending': 'قيد الانتظار',
            'In Progress': 'جاري العمل',
            'Resolved': 'تم الحل',
            'Rejected': 'تم الرفض',
        }
        status_ar = status_ar_map.get(instance.status, instance.status)

        if instance.status in ['In Progress', 'Resolved','Rejected']:
            # Notify reporter
            Notification.objects.create(
                user=instance.reporter,
                issue=instance,
                notification_type='issue_update',
                message=f"تحديث لحالة بلاغك رقم {instance.id}: البلاغ الآن {status_ar}."
            )
            # Notify others in the city
            from django.contrib.auth import get_user_model
            User = get_user_model()
            users_in_city = User.objects.filter(city__iexact=instance.city).exclude(id=instance.reporter.id)
            notifications = [
                Notification(
                    user=user,
                    issue=instance,
                    notification_type='city_alert',
                    message=f"تحديث لبلاغ في {instance.city}: الحالة الآن {status_ar}."
                ) for user in users_in_city
            ]
            Notification.objects.bulk_create(notifications)


class UserProfileView(APIView):
    """GET/PATCH /api/profile/  → current user info for the frontend."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_supervisor = hasattr(user, 'supervisor')
        image_url = None
        if user.image:
            image_url = request.build_absolute_uri(user.image.url)
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
            'phone': getattr(user, 'phone', ''),
            'governorate': getattr(user, 'governorate', ''),
            'city': getattr(user, 'city', ''),
            'is_supervisor': is_supervisor,
            'image': image_url,
        })

    def patch(self, request):
        user = request.user
        serializer = UserProfileUpdateSerializer(
            user, data=request.data, partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.select_related('issue').all()

class NotificationReadView(APIView):
    """PATCH /api/notifications/<id>/read/"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)


class UserIssueStatsView(APIView):
    """
    GET /api/issues/my/stats/
    Returns statistics for the authenticated user's reported issues:
    - total_issues: total count
    - by_status: {pending, in_progress, resolved, rejected}
    - by_category: {lighting, pothole, speed_bump, traffic_sign, road_damage, other}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_issues = Issue.objects.filter(reporter=request.user)

        # Aggregate counts by status
        status_counts = user_issues.aggregate(
            pending=Count('id', filter=Q(status='Pending')),
            in_progress=Count('id', filter=Q(status='In Progress')),
            resolved=Count('id', filter=Q(status='Resolved')),
            rejected=Count('id', filter=Q(status='Rejected')),
        )

        # Aggregate counts by category
        category_counts = user_issues.aggregate(
            lighting=Count('id', filter=Q(category='lighting')),
            pothole=Count('id', filter=Q(category='pothole')),
            speed_bump=Count('id', filter=Q(category='speed_bump')),
            traffic_sign=Count('id', filter=Q(category='traffic_sign')),
            road_damage=Count('id', filter=Q(category='road_damage')),
            other=Count('id', filter=Q(category='other')),
        )

        return Response({
            'total_issues': user_issues.count(),
            'by_status': status_counts,
            'by_category': category_counts,
        })


class RegisterDeviceTokenView(APIView):
    """
    POST /api/device-token/
    Body: { "token": "FCM_TOKEN" }

    Registers (or re-activates) an FCM device token for the authenticated user.
    If the token already exists for a different user, it is reassigned.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        from .models import DeviceToken

        # update_or_create keyed on the token itself.
        # If the token exists (maybe for another user), reassign it.
        obj, created = DeviceToken.objects.update_or_create(
            fcm_token=token,
            defaults={
                'user': request.user,
                'is_active': True,
            },
        )

        return Response(
            {'status': 'created' if created else 'updated'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
