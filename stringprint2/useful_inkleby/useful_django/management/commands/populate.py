from django.core.management import BaseCommand
from importlib import import_module
from django.apps import apps as project_apps

class Command(BaseCommand):
    """
    Example usage:
    
    manage.py populate
    manage.py populate appname
    
    Looks for an app/populate.py and runs
    a populate function
    
    """
    help = "Enter an app to populate"
    
    def add_arguments(self, parser):
        parser.add_argument('app', nargs='*', type=str)
    

    def handle(self, *args, **options):
        apps = options['app']
        if len(apps) == 0:
            apps = [x.name for x in project_apps.get_app_configs()]
        for app in apps:
            try:
                app = import_module(app +".populate")
            except ImportError:
                continue
            
            app.populate()
            