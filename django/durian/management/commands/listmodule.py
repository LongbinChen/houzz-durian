import os

from django.core.management.base import BaseCommand, CommandError
from durian.JobRunner import JobRunner
from durian.models import Pipe
from durian.settings import *
import durian.durianutils as durianutils


class Command(BaseCommand):
    help = 'list all available pipe'

    def add_arguments(self, parser):
        # Positional arguments
        #parser.add_argument('--pipe_type', type = str, default=None)
        pass

    def handle(self, *args, **options):
        app_dict = durianutils.get_apps()
        module_list = durianutils.get_modules()
        print "%d app(s) found : %s " % (len(app_dict) , ",".join(app_dict))
        print "%d modules  found :" % (len(module_list) )
        for i, k in  enumerate(module_list):
            print  "%d : %s " %(i, k)
