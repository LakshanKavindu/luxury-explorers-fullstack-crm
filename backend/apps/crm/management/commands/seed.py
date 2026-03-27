"""
Management command to seed the database with demo data.
Useful for testing pagination, tenant isolation, and UI layouts.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import random
import string

from apps.accounts.models import Organization, User
from apps.crm.models import Company, Contact

class Command(BaseCommand):
    help = "Seeds the database with test Organizations, Users, Companies, and Contacts."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            Organization.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        with transaction.atomic():
            # ─────────────────────────────────────────────────────────────────
            # 1. Create Organizations
            # ─────────────────────────────────────────────────────────────────
            acme_org = Organization.objects.create(name="Acme Corp", plan=Organization.Plan.PRO)
            globex_org = Organization.objects.create(name="Globex Inc", plan=Organization.Plan.BASIC)

            self.stdout.write(self.style.SUCCESS("Created Organizations: Acme Corp, Globex Inc"))

            # ─────────────────────────────────────────────────────────────────
            # 2. Create Users for Acme Corp
            # ─────────────────────────────────────────────────────────────────
            acme_users = [
                {
                    "email": "admin@acme.com",
                    "full_name": "Acme Admin",
                    "role": User.Role.ADMIN,
                },
                {
                    "email": "manager@acme.com",
                    "full_name": "Acme Manager",
                    "role": User.Role.MANAGER,
                },
                {
                    "email": "staff@acme.com",
                    "full_name": "Acme Staff",
                    "role": User.Role.STAFF,
                },
            ]

            for user_data in acme_users:
                user = User(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    organization=acme_org,
                )
                user.set_password("password123")  # Standard password for demo
                user.save()

            # Create a spy user for Globex to test tenant isolation
            globex_user = User(
                email="staff@globex.com",
                full_name="Globex Staff",
                role=User.Role.STAFF,
                organization=globex_org,
            )
            globex_user.set_password("password123")
            globex_user.save()

            self.stdout.write(self.style.SUCCESS("Created 3 users for Acme, 1 user for Globex. Password is 'password123'."))

            # ─────────────────────────────────────────────────────────────────
            # 3. Create Companies and Contacts
            # ─────────────────────────────────────────────────────────────────
            industries = ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing", "Energy", "Software"]
            
            # Helper to generate companies and contacts
            def generate_data(org, num_companies):
                companies = []
                countries = ["United States", "United Kingdom", "Canada", "Australia", "Germany", "France", "Japan"]
                for i in range(num_companies):
                    company_name = f"Demo Company {i+1} {random.choice(['LLC', 'Inc', 'Group', 'Partners'])}"
                    company = Company.objects.create(
                        organization=org,
                        name=company_name,
                        industry=random.choice(industries),
                        country=random.choice(countries),
                    )
                    companies.append(company)
                    
                    # 1-3 contacts per company
                    for j in range(random.randint(1, 3)):
                        Contact.objects.create(
                            organization=org,
                            company=company,
                            full_name=f"Contact {j+1} of {company_name}",
                            email=f"contact{j+1}_{i+1}@example.com",
                            phone="".join(random.choices(string.digits, k=11)),
                            role=random.choice(["Director", "Manager", "Engineer", "Consultant", "Specialist"]),
                        )
                return companies

            self.stdout.write(self.style.WARNING("Generating 30 companies for Acme Corp (to test pagination)..."))
            generate_data(acme_org, 30)

            self.stdout.write(self.style.WARNING("Generating 5 companies for Globex Inc (to test tenant isolation)..."))
            generate_data(globex_org, 5)

        self.stdout.write(self.style.SUCCESS("Database successfully seeded!"))
        self.stdout.write(self.style.SUCCESS("Ready to test: login with admin@acme.com / password123"))
