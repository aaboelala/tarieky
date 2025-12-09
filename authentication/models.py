
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser , BaseUserManager

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    governorate = models.CharField(max_length=15, blank=False) 
    city = models.CharField(max_length=15, blank=False)
    phone= models.CharField(max_length=11, blank=True, null=True)
    email = models.EmailField(unique=True)  
    REQUIRED_FIELDS = []     
    username = None
    USERNAME_FIELD = 'email'
    objects = UserManager()


    def __str__(self):
        return f"Citizen: {self.email}"


class Supervisor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='supervisor')
    phone = models.CharField(max_length=20)
    government_document = models.FileField(upload_to='supervisor_docs/')
    is_verified = models.BooleanField(default=False)  # الأدمن يوافق عليه بعد رفع الوثيقة

    def __str__(self):
        return f"Supervisor: {self.user.username} ({self.province})"



# Create your models here.

class ResetPasswordCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_codes')
    code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    reset_token = models.CharField(max_length=64, blank=True, null=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"ResetPasswordCode for {self.user.email} - Code: {self.code}"
    
    def is_expired(self):
        return self.created_at < timezone.now() - timedelta(minutes=5)  # 5 minutes expiration
    

class SignupOTP(models.Model):
    email = models.EmailField()
    code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    verification_token = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return f"SignupOTP for {self.email} - Code: {self.code}"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)
