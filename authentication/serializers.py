
from rest_framework import serializers
from .models import User ,Supervisor , SignupOTP


class Userserializer(serializers.ModelSerializer):
    verification_token = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone', 'email', 'governorate', 'city', 'password', 'verification_token']
        extra_kwargs = {
            'password': {'write_only': True , 'min_length': 8 },
            'first_name': {'required': True},       
            'last_name': {'required': True},
            
        }

    def validate(self, attrs):
        email = attrs.get('email')
        token = attrs.get('verification_token')

        # تأكيد التوكن
        try:
            otp = SignupOTP.objects.get(email=email, verification_token=token)
        except SignupOTP.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification token")

        # لو عايز تمسحه بعد الاستخدام
        otp.delete()

        return attrs
    

    def create(self, validated_data):
        validated_data.pop('verification_token', None)  # إزالة التوكن من البيانات
        user=User.objects.create_user(**validated_data)
        return user


class SupervisorSerializer(serializers.ModelSerializer):
    user=Userserializer(read_only=True)  
    class Meta:
        model=Supervisor
        fields=['province' ,' phone', 'government_document','is_verified', 'user' ]


    def create(self, validated_data):
        user=Supervisor.objects.create_user(**validated_data)
        return user

