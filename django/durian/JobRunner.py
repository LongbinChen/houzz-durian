import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import types
from time import gmtime, strftime

import yaml
from django.contrib.auth.models import Group, User
from django.db import connection
from django.utils import timezone
from durian.durianutils import *
from durian.models import Data, Job, JobDependency, Pipe
from durian.settings import *


class JobRunner:
    '''
        The class to run a job. take an job config as input,
        fetech the data, run the command, and copy the data
        to stroage place. 
    '''

    def _update_job_status(self, job, status):
        job.status = status
        job.save()
        job_hash = job.job_hash
        all_latched_jobs = Job.objects.filter(job_hash=job_hash)
        for j in all_latched_jobs:
            j.status = status
            j.save()
            if (status == Job.COMPLETED):
                JobDependency.objects.filter(job_name_src=j.job_name).update(status='removed')

    def _fail_job(self):
        self.job.status = Job.FAILED
        self.job.save()
        sys.exit()

    def _run_command(self, cmd):
        self._cmd_count += 1
        self.info("Running command %d: %s " % (self._cmd_count, cmd))
        try:
            with open(os.path.join(self.job_dir, "stdout_%d.txt" % self._cmd_count), "wb") as out:
                with open(os.path.join(self.job_dir, "stderr_%d.txt" % self._cmd_count), "wb") as err:
                    result = subprocess.Popen(cmd, shell=True, stdout=out, stderr=err)
                    streamdata = result.communicate()[0]
                    text = result.returncode
            if (text != 0):
                self.info("Status : FAIL")
                self.info("\n".join(open(os.path.join(
                    self.job_dir, "stderr_%d.txt" % self._cmd_count), "r").readlines()))
                self._fail_job()
        except subprocess.CalledProcessError as exc:
            self.info("Status : FAIL", exc.returncode, exc.output)
            self._fail_job()

    def __init__(self, job):

        self.job = job
        self.job_name = job.job_name
        self.pipe_name = job.pipe.pipe_name
        self.debug = True
        self.job_dir = os.path.join(working_directory, "job", str(self.job.id))

        self.run_log_file = '%s/__run_logfile' % self.job_dir
        self._cmd_count = 0
        self.data_conf = {}
        self.current_task = "Init"

    def _copy_source_data_to_cache(self, data_name, data_hash):
        cache_data_path = os.path.join(cached_data_directory, data_hash)
        if data_name.startswith("s3://"):
            self.info("s3: %s ----->>> %s" % (data_name, cache_data_path))
            self._run_command("s3cmd get %s %s " % (data_name, cache_data_path))
            with open(cache_data_path + ".info", "w") as finfo:
                finfo.write("downloaded time: " + strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) + "\n")
                self.info("downloaded time: " + strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) + "\n")
                finfo.write("data source: %s\n" % data_name)
            return True
        if data_name.startswith("http://") or data_name.startswith("https://"):
            self.info("https: %s ----->>> %s" % (data_name, cache_data_path))
            self._run_command("wget %s %s " % (data_name, os.path.join(self.job_dir, cache_data_path)))
            with open(cache_data_path + ".info", "w") as finfo:
                finfo.write("downloaded time" + strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) + "\n")
            return True
        return False

    def _unzip_data(self, zipfilename):
        dir_path = os.path.dirname(zipfilename)
        fname = os.path.basename(zipfilename)
        tmpfile = os.path.join(dir_path, "tmp_" + fname)
        # step 1. rename to tmp file

        self._run_command("mv %s %s " % (zipfilename, tmpfile))
        # step 2. create target directory
        self._run_command("mkdir %s " % (zipfilename))
        # step 3. unzip
        self._run_command("tar zxvf %s -C %s --strip-components=1" % (tmpfile, zipfilename))

    def _create_working_directory(self):
        if not os.path.exists(self.job_dir):
            os.makedirs(self.job_dir)

    def _create_default_config_file(self):
        self.default_config_file = os.path.join(self.job_dir, "_default_config")
        for inp, v in self.job_conf["input"].items():
            if isinstance(v, types.ListType):
                for i, dv in enumerate(v):
                    self.job_conf["input"][inp][i] = self.pipe_def['datafile'][dv]
            else:
                self.job_conf["input"][inp] = self.pipe_def['datafile'][v]

        for inp, v in self.job_conf["output"].items():
            if isinstance(v, types.ListType):
                for i, dv in enumerate(v):
                    self.job_conf["output"][inp][i] = self.pipe_def['datafile'][dv]
            else:
                self.job_conf["output"][inp] = self.pipe_def['datafile'][v]

        with open(self.default_config_file, "w") as cf:
            # translate input and outputs in job_conf
            yaml.safe_dump(self.job_conf, cf, default_flow_style=False)

    def _copy_module_to_working_directory(self):
        module_name = self.job_conf["module"]
        flds = module_name.split("/")
        repo = flds[0]
        repo_directory = os.path.join(resource_directory, repo)
        symlink_force(repo_directory, os.path.join(self.job_dir, repo))

    def _link_file_from_storage(self, file_hash, data_name):
        '''
        link input files to job directory
        '''
        if local_storage:
            storage_location = os.path.join(storage_path, file_hash)
            current_location = os.path.join(self.job_dir, data_name)
            if not os.path.exists(storage_location):
                print "============="
                print "[ERROR]"
                print "It seems the input file '%s', which is linked "
                print "to %s, doesn't exist. Please make sure the dependent jobs"
                print "are completed" % (data_name, storage_location)
                self._fail_job()
            symlink_force(storage_location, current_location)
            self.info("%s -> %s " % (data_name, storage_location))

    def _remove_output_softlink(self):
        for data_name, data_hash in self.job_conf["output"].items():
            output_file = os.path.join(self.job_dir, data_name)
            if os.path.islink(output_file):
                os.unlink(output_file)
                self.info("unlink %s" % data_name)

    def _upload_data_to_s3(self, local_file, s3_path):
        cmd = "s3cmd put %s %s " % (local_file, s3_path)
        self._run_command(cmd)

    def _move_file_to_storage(self, data_name, file_hash):
        '''
        move the file to storage, and create a symbolic link to the new destiation
        '''

        if local_storage:
            # create storage directory
            cmd = "mkdir -p %s" % storage_path
            os.system(cmd)
            storage_file_path = os.path.join(storage_path, file_hash)
            if os.path.exists(storage_file_path):
                cmd = "rm -r %s" % storage_file_path
                self._run_command(cmd)
                # shutil.rmtree(storage_file_path)
            cmd = "mv %s %s" % (os.path.join(self.job_dir, data_name), storage_file_path)
            self._run_command(cmd)
            storage_file = os.path.join(storage_path, file_hash)
            data_file = os.path.join(self.job_dir, data_name)
            symlink_force(storage_file, data_file)
            self.info("moved data from %s to %s and soft-linked is created . " % (storage_file, data_file))
        else:
            self.info("non-local storage hasn't been implemented yet.")

    def _attach_or_copy_source_data(self, inputfile, filemd5, data_key, unzip=False):
        if inputfile.startswith("file://"):
            filename = os.path.join(resource_directory, inputfile.replace("file://", ""))
            symlink_force(filename, os.path.join(self.job_dir, data_key))
            if unzip:
                self._unzip_data(os.path.join(self.job_dir, data_hash))
            self.info("%s -> %s" % (data_key, filename))
            return True

        # s3 or http files, download to cached directory first and then create soft link

        cached_data_file = os.path.join(cached_data_directory, filemd5)

        if not os.path.exists(cached_data_file):
            self._copy_source_data_to_cache(inputfile, filemd5)
            if unzip:
                self._unzip_data(cached_data_file)

        # create symbolic link
        symlink_force(cached_data_file, os.path.join(self.job_dir, data_key))
        self.info("%s -> %s <--download-- %s " % (data_key, cached_data_file,  inputfile))

        return True

    def _prepare_data(self, resource_link, data_name, unzip):
        if '://' in resource_link:
            self._attach_or_copy_source_data(resource_link, get_md5(resource_link), data_name, unzip)
        elif resource_link in self.pipe_def["datafile"]:
            self._link_file_from_storage(self.pipe_def["datafile"][resource_link], data_name)
        else:
            self.info("[ERROR] Don't know how to get the data '%s' " % resource_link)
            self._fail_job()

    def _prepare_data_to_working_directory(self):
        self.current_task = "Data"
        self.info("--- Preparing Job Data : %s --- " % (self.job_dir))
        for d, v in self.job_conf["input"].items():
            if not isinstance(v, types.ListType):
                #self._download_data(v, d, self.job_conf["input"][d].get("unzip", False))
                self._prepare_data(v, d, self.module["input"][d].get("unzip", False))
            else:
                for di, dv in enumerate(v):
                    data_name = "%s_%d" % (d, di)
                    self._prepare_data(dv, data_name, False)
        print ""

    def _copy_output_to_storage(self):
        self.info("Copy data to storage place")
        for data_name, data_hash in self.job_conf["output"].items():
            self._move_file_to_storage(data_name, data_hash)

    def _translate_data_name(self, pipe_name, dn):
        return self.pipe_def["datafile"].get(dn, dn)

    def _get_data_hash_from_db(self, pipe_name, data_name):
        full_data_name = self.get_full_data_name(pipe_name, data_name)
        try:
            da = Data.objects.get(data_name=full_data_name)
            v = da.data_hash
        except Data.DoesNotExist:
            v = data_name
        return v

    def run_job(self):
        self.current_task = "Run"
        self.output_data_hash = []
        if (run_local):
            cmd_template = self.module["cmd"]
            flds = cmd_template.split(" ")
            trans_flds = []
            for f in flds:
                if "input" in self.module and f in self.job_conf["input"]:
                    if isinstance(self.job_conf["input"][f], types.ListType):
                        for fi, fv in enumerate(self.job_conf["input"][f]):
                            data_name = "%s_%d" % (f, fi)
                            trans_flds.append(data_name)
                    else:
                        trans_flds.append(f)
                elif "output" in self.module and f in self.module["output"]:
                    trans_flds.append(f)
                elif "parameters" in self.module and f in self.module["parameters"]:
                    trans_flds.append(str(self.job_conf.get("parameters", {}).get(
                        f, self.module["parameters"][f].get('default', None))))
                else:
                    trans_flds.append(f)
            trans_cmd = " ".join(trans_flds)
            self.info("run command:'%s' at working directory: %s " % (trans_cmd, self.job_dir))
            try:
                logfile = open(self.run_log_file, 'w')
                proc = subprocess.Popen(trans_cmd, shell=True, cwd=self.job_dir,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
                self.info("process id is %d" % proc.pid)
                self.job.process_id = proc.pid
                self.job.start_at = timezone.now()
                self.job.end_at = None
                connection.close()
                self.job.save()
                with proc.stdout:
                    for line in iter(proc.stdout.readline, b''):
                        sys.stdout.write(line)
                        logfile.write(line)
                returncode = proc.wait()

                connection.close()
                self.job.end_at = timezone.now()
                self.job.status = Job.COMPLETED
                self.job.process_id = None
                self.job.save()
            except KeyboardInterrupt:
                connection.close()
                self.info("Job canceled from command line")
                self.job.end_at = timezone.now()
                self.job.status = Job.CANCELED
                self.job.process_id = None
                self.job.save()

            except Exception, e:
                connection.close()
                self.info(str(e))
                self.job_status = Job.FAILED
                self.job.process_id = None
                self.job.save()

    def remove_working_dir(self):
        os.system("rm -rf %s" % self.job_dir)

    def info(self, msg, task=None):
        if task == None:
            task = self.current_task
        if task != "":
            task = ":" + task
        msg_str = "[job %d%s] %s" % (self.job.id, task, msg)
        with open(self.job_dir + "/__log__.txt", "a") as logf:
            logf.write(msg_str + "\n")
            print(msg_str)

    def run(self):
        self._create_working_directory()

        self.job.status = Job.RUNNING
        self.job.machine_name = DURIAN_MACHINE_NAME
        self.job.save()
        job = Job.objects.get(job_name=self.job_name)
        self.job = job
        print ""
        self.info("Job id: %d" % self.job.id)
        self.info("Job name: %s" % self.job_name)
        self.info("Pipe name: %s " % self.job.pipe.pipe_name)
        self.info("Machine Running this job: %s " % self.job.machine_name)
        print ""
        self.job_conf = json.loads(job.job_conf)
        self.pipe_def = json.loads(self.job.pipe.pipe_def)

        module = get_config_by_path(self.job.module_id)
        self.module = module

        self._copy_module_to_working_directory()
        self._remove_output_softlink()
        self._prepare_data_to_working_directory()
        self._create_default_config_file()
        self.run_job()
        self.current_task = "Output"

        if (self.job.status == Job.COMPLETED):
            self._copy_output_to_storage()

        self._update_job_status(self.job, self.job.status)
