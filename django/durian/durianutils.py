import uuid
import os
from settings import * 
import yaml
import json
import hashlib
import errno
from durian.models import Job


SQL_GET_NEXT_EXCUTABLE_JOB = ''' SELECT * FROM durian_job j WHERE j.status = 'created' AND j.latched_to = "" AND j.job_name not in ( SELECT job_name_tgt FROM durian_jobdependency WHERE status = "created" ) '''


def get_next_excutable_job():
    executable_jobs =  Job.objects.raw(SQL_GET_NEXT_EXCUTABLE_JOB)
    count = 0
    first_job = None
    for j in executable_jobs:
        #print "%s, %s " %( j.id, j.job_name)
        first_job = j
        count += 1
    if (first_job):
        print "%d job can be executed now  while job %d is picked to be run" % (count, first_job.id)

    return first_job

def get_full_data_name(pipe_name, data_name):
   return pipe_name + "." + data_name

def get_full_job_name(pipe_name, job_name):
   return pipe_name + ">" + job_name



#loading a json object by resource path like durianml::pipe::mnist::key1::key2::..::keyn
'''
def load_resource(resource_path):
   flds = resource_path.split("::")
   config_file_path = "::".join(flds[:3])
   key_path = flds[3:]
   filename = self.get_config_by_name(config_file_path) 
   resource = None
   with open(filename, 'r') as f:
      try:
        resource = yaml.load(f)
      except yaml.YAMLError as exc:
        print(exc)
        return  None
   for k in key_path:
      resource = resource[k]
   return resource
'''
def create_uuid(self):
   return uuid.uuid4()


def get_config_by_path(file_path):
  full_path = get_full_path(file_path)
  if not file_path.endswith(".yaml"): full_path += ".yaml"
  with open(full_path, 'r') as f:
    try:
      resource = yaml.load(f)
    except yaml.YAMLError as exc:
      print(exc)
      return  None
  return resource
  

def  get_full_path(file_path):
  return os.path.join(resource_directory, file_path)

def get_md5( input_str):
  m = hashlib.md5()
  m.update(input_str)
  return m.hexdigest()


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()





def get_main_file_md5(file_path):
  md5_py = ""
  main_file_name = get_full_path(file_path) 
  if not main_file_name.endswith(".py"): main_file_name += ".py"
  if os.path.exists(main_file_name):
     #print("check sum of file %s is %s " % (main_file_name, md5(main_file_name)))
     md5_py = md5(main_file_name)
  else:
     print("can not find file %s " % (main_file_name))

  md5_yaml = ""
  yaml_file_name = get_full_path(file_path) 
  if not yaml_file_name.endswith(".yaml"): yaml_file_name += ".yaml"
  if os.path.exists(yaml_file_name):
     #print("check sum of file %s is %s " % (yaml_file_name, md5(yaml_file_name)))
     md5_yaml = md5(yaml_file_name)
  else:
     print("can not find file %s " % (yaml_file_name))
  
  return md5_py + "." + md5_yaml
   
 
def symlink_force(target, link_name):
    try:
        os.symlink(target, link_name)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(link_name)
            os.symlink(target, link_name)
        else:
            raise e 

def hardlink_force(target, link_name):
    try:
        os.link(target, link_name)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(link_name)
            os.link(target, link_name)
        else:
            raise e 
