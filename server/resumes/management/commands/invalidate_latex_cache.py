from django.core.management.base import BaseCommand

from resumes.models import Resume


class Command(BaseCommand):
    help = (
        "Set latex_cache_valid=False for all resumes. "
        "Run this after re-seeding templates to force re-assembly with the new preamble."
    )

    def handle(self, *args, **options):
        count = Resume.objects.filter(latex_cache_valid=True).update(latex_cache_valid=False)
        self.stdout.write(
            self.style.SUCCESS(f"Invalidated LaTeX cache for {count} resume(s).")
        )
