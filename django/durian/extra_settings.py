# This file contains all local settings

# Durian directory containing cached data, working and storage directories
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
durian_directory = '/data/durian'
resource_directory =  BASE_DIR + "/../" + "resource/"
working_directory = os.path.join(durian_directory, "working")
cached_data_directory = os.path.join(durian_directory, "cached_data")

local_storage = True
s3_storage = False
storage_path = os.path.join(durian_directory, "storage")

run_local = True
DJANGO_BOOTSTRAP_UI_THEME = 'bootswatch-cosmo'

DURIAN_MACHINE_NAME = "slave1"

resource_directory = '/home/ubuntu/durian/resource'
