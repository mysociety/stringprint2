from __future__ import absolute_import

from importlib import import_module
import os

from dirsync import sync

from django.core.management import BaseCommand
from django.conf import settings
from django.apps import apps as project_apps
from ...views import AppUrl
from ...views.bake import BaseBakeManager

class Command(BaseCommand):
    """
    example usage:

    manage.py bake
    manage.py bake appname
    
    When it examines an app will look for:
    
    A bake.py with a bake function
    A views module with a BakeManager subclassed from BaseBakeManager
    A views module using views subclassed from BakeView
    """
    help = "Enter an app to bake, or no app label to bake all apps"
    
    def add_arguments(self, parser):
        parser.add_argument('app', nargs='*', type=str,default=[])

    
    def handle(self, *args, **options):
        apps = options['app']
        kwargs = [x for x in apps if "=" in x]
        apps = [x for x in apps if x not in kwargs]
        kwargs = [x.split("=") for x in kwargs]
        kwargs = {x:y for x,y in kwargs}
        
        if len(apps) == 0:
            apps = [x.name for x in project_apps.get_app_configs()]
        for app in apps:
            manager = None
            try:
                bake_module = import_module(app +".bake")  
            except ImportError:
                bake_module = None
                
            try:
                views_module = import_module(app +".views")  
            except ImportError:
                views_module = None                
            #run custom bake command
            if bake_module:
                if hasattr(bake_module,"bake"):
                    bake_module.bake()
                    continue
                
            if views_module:
                if bake_module and hasattr(bake_module,"BakeManager"):
                    manager = bake_module.BakeManager(views_module)
                else:
                    manager = BaseBakeManager(views_module)
            if manager:
                manager.bake(**kwargs)
