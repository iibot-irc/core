#!/usr/bin/env python
import json
import sys
from os.path import expanduser

def config(name):
  return json.load(open(expanduser('~') + '/etc/iibot.conf'))[name]

if __name__ == '__main__':
  print config(sys.argv[1])
