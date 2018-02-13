# Durian


## Introduction
Durian is a machine learning utility tool to facilitate machine learning tasks. It is a dev tool to manage pipe/jobs and it fetches data and module files and execute the modules on server; and store the output on s3 (or other storage space).

It modularizes each machine learning algorithms in to 'modules', which are used to build complicate machine learning training process (pipes). In Pipes, the data are either stored in s3, or in git repos or https URIs. Local file will be supported soon.   

We are working on a Web UI to create/edit/maintain training process and visualize the training process pipes.

## Get started

### Installation


use sudo apt-get install to install following packages; please don't change the default admin name as root and remmeber the password for root. 
```
sudo apt-get update
sudo apt-get install python-pip python-dev libmysqlclient-dev
```

if you are using mysql as the backend database, you also need to install mysql. By default, durian uses sqlite for simplicity.

```
sudo apt-get install mysql-server 
```



#### clone durian

```
mkdir workspace; cd workspace;
git clone git@github.com:Houzz/houzz-durian.git

```

create an alias 'dr'  in your ~/.bash_profile, assuming you clone durian repo at /home/ubuntu/workspace/. Otherwise you need to update the alias to the right location

```
alias dr='python /home/ubuntu/workspace/durian/django/manage.py' 
```



#### create mysql user mlusers with passwd mlusers
from durian directory
```
mysql -u root -p < django/init.sql
```

install python packages 

```
sudo pip install -r requirements.txt
```

run the following to create database and create user/group durian

```
dr migrate
dr init_durian
dr makemigrations durian
dr migrate durian
```


#### Config
there are a few import config you need to set up before you can run durian. you can run the following command to view the config views. 

```
dr config
```

These are the directory to save intermedia data and download/cached datas. For some experiment, the file size might be very large so make sure you config a large enough directory. 


You can create a file 'extra_settings.py' if you need to configure your own settings without changing the remote repo. See local_settings_sample.py regarding what you might want to configure.

```
vi django/durian/extra_settings.py
```


## Using Durian
### all the commands
```
dr 
```

### list all available pipe
```
dr listpipe
```
### run a pipe 

``` 
dr runpipe text_classification/pipe/bow_model.yaml
``` 
### list all the jobs 

``` 
dr listjob
``` 

### run a job 

``` 
dr runjob --job_id [job_id]
``` 


## Concepts in Durian



### App
   Each app is a directory contains subdirectories data, module and pipe. It is a collection of training data, training algorithm and pipelines. You can define an app by create a directory and mount to durian. 
 
   
    
   

### Data

Data in Durian has two types, one is external data and one is intermedia data in the training process

External Data is stored either at s3, or a file at git repo or a file downloadable from internet. Therefore we can represent a data as one of the following three format:

```
 s3://path/to/your/s3/file/test_room_nostopwords
 file://text_classification/data/train_data
 http://www.example.com/train.data.tar.gz
```

Durian Daemon will automatically fetch and/or download data from s3, git repo or https

Intermedia Data are the output for one jobs and will be used as the input of other jobs in the same pipe. In the pipe defintion, they are represented using a unique data name in the pipe. See the pipe examples for more details. 


### Module

A module is a predefined code, wrapped with a yaml file interface definition, with specified input/output and command lines to run the module

```
input:
    train_data:
        type: text
        optional: false
        datafile: true
    test_data:
        type: text
        optional: false
        datafile: true
    category_label:
        type: text
        optional: false
        datafile: true

output:
    model:
        type: sk_sgd_pickle
        optional: false
        datafile: true

parameters:
    num_epochs:
        type: int
        default: 5

cmd: python -m text_classification.module.bow_model --num_epochs num_epochs category_label train_data test_data model
```

> If you write your command in python with standard argparser library, we created a command tool for you to create the yaml interface definition file for you. 

For example, 

```
dr create_yaml $DURIAN/apps/durian/module/upload_to_s3.py
```



### Jobs and Pipe

A job is an instance of module, with inputs and parameters set by the yaml configs. 

A pipe is a set of jobs defining the data flows, where the inputs and outputs of the jobs are connected together. 

A pipe is usually a complete pipeline to finish a task, which usually includes data preprocessing, training, evaluation, and result analysis.

An example of pipe with only one job is a yaml file looks like:

```
version: 1.0
jobs:
  bow_model:
      module: text_classification/module/bow_model
      input:
        train_data: [input your s3 address here]
        test_data: [input your s3 file address here]
        category_label: [input your s3 file address here]
      output:
        model: bow_model_model
```

### Job Caching


Internally, we want to avoid duplication of running the example same jobs. In the case that the module's output is deterministic of the input data and parameters (in most case, we can assume that even for random algorithms), we use the hash value of the concatenated string from module_id, md5 of souced_code, input and parameters identify a job. We can create a unique hash for each output data as well using the similar method by adding the output name in computing the hash. 

```
job_hash = md5 ("\t".join[ module_id + md5(source _code of module), input_list, param_list])
data_hash = md5 ("\t".join[ module_id + md5(source _code of module), input_list, param_list, outputname])
```

In running a pipe, we calculate the data hash and job hash for each job and each data. If we found we already have run the job before and the data are cached, we can skip running the job and fetch the data directly from our storage system. 

### External Data Caching
it is usually time consuming to download external data. In Durian, all external data are downloaded and cached. the cached folder is config at durian/django/durian/settings.py file


### Job Scheduling


### S3 Setup
You need to config your s3 access by setting the file ~/.s3cfg
```
aws --configure
s3cmd --configure
```

### about the authors
  Durian was created by @lilia when she was an intern at Houzz's research team in Summer 2017. Since then, @longbin, @xinai @yangli all contribute to durian
  

