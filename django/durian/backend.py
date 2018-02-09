from durian.models import Pipe, Job, JobDependency, Data
from django.contrib.auth.models import User, Group
import yaml
import json
import time
import os
import sys
import subprocess
from durian.settings import * 
import types
import durianutils
from time import gmtime, strftime

   
def get_apps():
    return [o for o in os.listdir(resource_directory) if os.path.isdir(os.path.join(resource_directory, o))] 


def get_modules():
    module_list = []
    for root, dirs, files in os.walk(resource_directory, followlinks=True):
       path = root.split(os.sep)
       if (len(path) < 2): continue
       if path[-1] == "module":
        for file in files:
          if file.endswith(".yaml"):
             py_file = file[:-5] + ".py"
             if os.path.exists(os.path.join(root, py_file)):
                module_list.append(os.path.join(path[-2], path[-1], file))
    return module_list
