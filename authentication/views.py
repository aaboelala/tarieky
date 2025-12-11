import json
import random
import secrets
import string
from zipfile import Path
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics , permissions , mixins , status

from .utils import send_async_email
from .serializers import Userserializer , SupervisorSerializer
from .models import ResetPasswordCode, User , Supervisor , SignupOTP 
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import send_mail


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = Userserializer
    permission_classes = [permissions.AllowAny]

class SupervisorRegistrationView(generics.CreateAPIView):
    queryset = Supervisor.objects.all()
    serializer_class = SupervisorSerializer
    permission_classes = [permissions.AllowAny]


#add endpont for return governorates and cities in json file
class GovernoratesCitiesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        file_path = settings.BASE_DIR / "static" / "data" / "egypt.json"
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return JsonResponse(data, safe=False)
    


####  OTP for reset password ####
    
class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        
        code = random.randint(1000, 9999)
        ResetPasswordCode.objects.create(user=user, code=code)
        send_mail(
            "Password Reset Code",
            f"Your reset code is {code}. It will expire in 5 minutes.",
            "trafficsystem@mailtrap.io",
            [email],
            fail_silently=False,
        )
        return Response({"message": "OTP sent successfully"}, status=200)

class VerifyOTPViewForForgetPass(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        try:
            user = User.objects.get(email=email)
            otp = ResetPasswordCode.objects.filter(user=user, code=code).latest('created_at')
        except (User.DoesNotExist, ResetPasswordCode.DoesNotExist):
            return Response({"error": "Invalid code or email."}, status=400)

        if otp.is_expired():
            return Response({"error": "Code expired!"}, status=400)
        
        # إنشاء reset_token عشوائي
        reset_token = secrets.token_urlsafe(32)
        otp.reset_token = reset_token
        otp.save()

        return Response({
            "message": "Code verified successfully",
            "reset_token": reset_token
        }, status=200)
    
class SetNewPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')

        try:
            user = User.objects.get(email=email)
            otp = ResetPasswordCode.objects.filter(user=user, reset_token=reset_token).latest('created_at')
        except (User.DoesNotExist, ResetPasswordCode.DoesNotExist):
            return Response({"error": "Invalid token or email."}, status=400)

        if otp.is_expired():
            return Response({"error": "Reset token expired!"}, status=400)

        user.set_password(new_password)
        user.save()

        # تعليم الرمز بأنه تم استخدامه
        otp.is_used = True
        otp.delete()

        return Response({"message": "Password reset successfully."}, status=200)
    


####  OTP for Signup ####


class SignUpOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required"}, status=400)
        
        # if User.objects.filter(email=email).exists():
        #     return Response({"error": "Email is already registered"}, status=400)
        


        code = random.randint(1000, 9999)

        SignupOTP.objects.create(
            email=email,
            code=code
        )

        send_async_email(
            "Your verification code",
            f"Your OTP is {code}. It expires in 5 minutes.",
            "trafficsystem@mailtrap.io",
            [email]
        )

        return Response({"message": "OTP sent successfully"}, status=200)


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        try:
            otp = SignupOTP.objects.filter(email=email, code=code).latest('created_at')
        except SignupOTP.DoesNotExist:
            return Response({"error": "Invalid email or code"}, status=400)

        if otp.is_expired():
            return Response({"error": "OTP expired"}, status=400)
        
        verification_token = secrets.token_urlsafe(32)
        otp.verification_token = verification_token
        otp.save()
        
        return Response({
            "message": "Email verified",
            "verification_token": verification_token
        }, status=200)
    
    

