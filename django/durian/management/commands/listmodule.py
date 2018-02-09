from django.core.management.base import BaseCommand, CommandError
from durian.models import Pipe
from durian.JobRunner import JobRunner
import os
from durian.settings  import *
from durian.backend import *

class Command(BaseCommand):
    help = 'list all available pipe'

    def add_arguments(self, parser):
        # Positional arguments
        #parser.add_argument('--pipe_type', type = str, default=None)
        pass

    def handle(self, *args, **options):
        app_dict = get_apps()
        module_list = get_modules()
        print "%d app(s) found : %s " % (len(app_dict) , ",".join(app_dict))
        print "%d modules  found :" % (len(module_list) )
        for i, k in  enumerate(module_list):
            print  "%d : %s " %(i, k)
   
