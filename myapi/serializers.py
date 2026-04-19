from rest_framework import serializers
from .models import Issue
from authentication.models import User


class ReporterSerializer(serializers.ModelSerializer):
    """Minimal user info embedded in issue responses."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'governorate', 'city']


class IssueListSerializer(serializers.ModelSerializer):
    """Used for the list view — lightweight."""
    reporter = ReporterSerializer(read_only=True)
    photo_url = serializers.SerializerMethodField()

    status = serializers.CharField(source='get_status_display', read_only=True)
    category = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'photo_url', 'description', 'status', 'category',
            'latitude', 'longitude', 'city', 'governorate',
            'created_at', 'reporter'
        ]

    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None


class IssueDetailSerializer(serializers.ModelSerializer):
    """Full detail including reporter info."""
    reporter = ReporterSerializer(read_only=True)
    photo_url = serializers.SerializerMethodField()

    status = serializers.CharField(source='get_status_display', read_only=True)
    category = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'photo_url', 'description', 'status', 'category',
            'latitude', 'longitude', 'city', 'governorate',
            'created_at', 'updated_at', 'reporter',
        ]

    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None


class IssueCreateSerializer(serializers.ModelSerializer):
    """Used when a mobile client creates a new issue."""
    class Meta:
        model = Issue
        fields = [
            'photo', 'description', 'category', 'latitude', 'longitude',
            'city', 'governorate',
        ]


class IssueStatusUpdateSerializer(serializers.ModelSerializer):
    """Supervisors can update the status only."""
    class Meta:
        model = Issue
        fields = ['status']

    def validate_status(self, value):
        instance = self.instance
        if not instance:
            return value

        current_status = instance.status
        new_status = value

        if current_status == 'Pending':
            if new_status not in ['In Progress', 'Rejected']:
                raise serializers.ValidationError(
                    "From Pending, you can only transition to 'In Progress' or 'Rejected'."
                )
        elif current_status == 'In Progress':
            if new_status not in ['Resolved', 'Rejected']:
                raise serializers.ValidationError(
                    "From In Progress, you can only transition to 'Resolved' or 'Rejected'."
                )
        elif current_status == 'Resolved' or current_status == 'Rejected':
            raise serializers.ValidationError(f"Issue is already {current_status} and cannot be changed.")

        return value


from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    notification_type = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'notification_type', 'created_at', 'issue']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Used for users to update their profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'city', 'governorate', 'image']


class DeviceTokenSerializer(serializers.Serializer):
    """Accepts an FCM device token for push notification registration."""
    token = serializers.CharField(max_length=255)

