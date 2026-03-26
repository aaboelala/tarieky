"""
Management command to seed the database with sample traffic issues.

Usage:
    python manage.py seed_issues
"""
import os
import io
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from authentication.models import User
from myapi.models import Issue

# Sample issues around Cairo, Egypt
SAMPLE_ISSUES = [
    {
        'description': 'Large pothole on the main road causing traffic delays and risk of vehicle damage.',
        'latitude': 30.0444,
        'longitude': 31.2357,
        'city': 'القاهرة',
        'governorate': 'القاهرة',
        'status': 'Pending',
    },
    {
        'description': 'Broken traffic light at a busy intersection. Cars are not stopping, dangerous situation.',
        'latitude': 30.0460,
        'longitude': 31.2340,
        'city': 'القاهرة',
        'governorate': 'القاهرة',
        'status': 'In Progress',
    },
    {
        'description': 'Road flooding due to broken water pipe. Water is covering the entire lane.',
        'latitude': 30.0430,
        'longitude': 31.2380,
        'city': 'الجيزة',
        'governorate': 'الجيزة',
        'status': 'Pending',
    },
    {
        'description': 'Missing road sign at highway exit. Drivers are confused about directions.',
        'latitude': 30.0500,
        'longitude': 31.2300,
        'city': 'القاهرة',
        'governorate': 'القاهرة',
        'status': 'Resolved',
    },
    {
        'description': 'Damaged guardrail on the bridge. Pieces of metal sticking out dangerously.',
        'latitude': 30.0480,
        'longitude': 31.2360,
        'city': 'القاهرة',
        'governorate': 'القاهرة',
        'status': 'Pending',
    },
    {
        'description': 'Illegal parking blocking the bus lane. Multiple vehicles parked.',
        'latitude': 30.0420,
        'longitude': 31.2350,
        'city': 'الجيزة',
        'governorate': 'الجيزة',
        'status': 'In Progress',
    },
    {
        'description': 'Cracked road surface on the highway. Multiple lanes affected.',
        'latitude': 30.0455,
        'longitude': 31.2320,
        'city': 'القاهرة',
        'governorate': 'القاهرة',
        'status': 'Pending',
    },
    {
        'description': 'Street light outage. Entire block is dark at night, very unsafe for pedestrians.',
        'latitude': 30.0470,
        'longitude': 31.2390,
        'city': 'الإسكندرية',
        'governorate': 'الإسكندرية',
        'status': 'Resolved',
    },
    {
        'description': 'Construction debris left on the road after work hours. No warning signs.',
        'latitude': 30.0440,
        'longitude': 31.2370,
        'city': 'القاهرة',
        'governorate': 'القاهرة',
        'status': 'Pending',
    },
    {
        'description': 'Road marking faded completely at a roundabout. Causing confusion among drivers.',
        'latitude': 30.0490,
        'longitude': 31.2330,
        'city': 'الجيزة',
        'governorate': 'الجيزة',
        'status': 'In Progress',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with sample traffic issues'

    def handle(self, *args, **options):
        # Create a demo user if none exists
        user, created = User.objects.get_or_create(
            email='demo@tarieky.com',
            defaults={
                'first_name': 'أحمد',
                'last_name': 'محمد',
                'governorate': 'القاهرة',
                'city': 'القاهرة',
            },
        )
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write(self.style.SUCCESS('Created demo user: demo@tarieky.com / demo1234'))

        # Create a placeholder image (1x1 red pixel PNG)
        # This is a minimal valid PNG so ImageField doesn't complain
        png_header = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx'
            b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        count = 0
        for i, data in enumerate(SAMPLE_ISSUES):
            if Issue.objects.filter(
                latitude=data['latitude'],
                longitude=data['longitude'],
                description=data['description'][:50],
            ).exists():
                continue

            issue = Issue(
                reporter=user,
                description=data['description'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                city=data['city'],
                governorate=data['governorate'],
                status=data['status'],
            )
            issue.photo.save(
                f'seed_issue_{i+1}.png',
                ContentFile(png_header),
                save=False,
            )
            issue.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {count} issues (skipped duplicates)'))
