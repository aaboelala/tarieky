from django.urls import path
from .views import GovernoratesCitiesView, VerifyOTPViewForForgetPass, ResetPasswordView,SetNewPasswordView, SupervisorRegistrationView, UserRegistrationView , SignUpOTPView , VerifyOTPView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    path('get-governorates-cities/', GovernoratesCitiesView.as_view(), name='get_governorates_cities'),

   
    path('supervisor-sign-up/', SupervisorRegistrationView.as_view(), name='supervisor-sign-up'),
    path('sign-up-otp/', SignUpOTPView.as_view(), name='sign-up-otp'),
    path('verify-sign-up-otp/', VerifyOTPView.as_view(), name='verify_sign_up_otp'),
    path('user-sign-up/', UserRegistrationView.as_view(), name='user-sign-up'),

    path('log-in/api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('confirm-reset-password/', VerifyOTPViewForForgetPass.as_view(), name='confirm_reset_password'),
    path('set-new-password/', SetNewPasswordView.as_view(), name='set_new_password'),
]