import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core import management

class Command(BaseCommand):
    help = 'Dumps the production postgres db into a JSON file as test data.'

    def handle(self, *args, **options):
        # Check if we are using the production database
        db_engine = settings.DATABASES['default']['ENGINE']
        if 'sqlite' in db_engine:
            self.stderr.write(self.style.ERROR("This command is intended to dump the production database, but is configured to use SQLite."))
            self.stderr.write(self.style.NOTICE("Please run this command with production settings, e.g., by unsetting DJANGO_SETTINGS_MODULE or running with the --settings flag."))
            return

        self.stdout.write("Starting the database dump process...")

        # Define the path for the output file
        output_dir = os.path.join(settings.BASE_DIR.parent, 'test_data')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'test_data.json')

        # List of apps to dump
        apps_to_dump = ['studies', 'auth']

        try:
            with open(output_file, 'w') as f:
                management.call_command(
                    'dumpdata',
                    *apps_to_dump,
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.permission',
                    format='json',
                    indent=4,
                    stdout=f
                )
            self.stdout.write(self.style.SUCCESS(f"Successfully dumped data for apps {', '.join(apps_to_dump)} to {output_file}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))
