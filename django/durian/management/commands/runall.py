from django.core.management.base import BaseCommand, CommandError
from durian.models import Pipe
from durian.durianutils import * 
from durian.JobRunner import JobRunner
import os

class Command(BaseCommand):
    help = 'run all jobs'

    def handle(self, *args, **options):
        next_job = get_next_excutable_job()
        while (next_job):
          jr = JobRunner(next_job)
          jr.run()
          next_job = get_next_excutable_job()
    
        print("no jobs can be run at this point of time")
