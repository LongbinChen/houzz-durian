from django.core.management.base import BaseCommand, CommandError
from durian.models import Pipe
from durian.JobRunner import JobRunner
import os
from durian.settings  import *

class Command(BaseCommand):
    help = 'list all available pipe'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('app_path', type = str, default=None)
        parser.add_argument('app_name', type = str, default=None)

    def handle(self, *args, **options):
        if not "app_path" in options: return
        app_path = options['app_path']
        app_name = options['app_name']
        print "adding app %s to durian as %s  " %  (app_path, app_name)
        if os.path.exists(app_path):
           os.symlink(app_path, os.path.join(resource_directory, app_name))

   
