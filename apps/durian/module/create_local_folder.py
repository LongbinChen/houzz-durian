import argparse
import gzip
import numpy
import os
import yaml
import types
import random

def run(args):
  os.system("ln -s %s %s" % (args.local_folder, args.output_folder))

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument( '--local_folder', default="/", type = str, help='the local directory')
  parser.add_argument( 'output_folder', type=str, help=' the output durian folder')

  args = parser.parse_args()
  run(args)
   
