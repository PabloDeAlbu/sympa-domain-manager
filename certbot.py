#!/usr/bin/env python3
#import pdb; pdb.set_trace()
import os
import sys
import shutil
import argparse
import subprocess
from datetime import datetime
from pwd import getpwnam

WEB_DOMAIN = '-d forums-test.rio20.net -d forums.achei.cl'
#arr = [WEB_DOMAIN,W2]
#certbot certificates | grep Domains: | sed 's/    Domains://g'  | sed 's/ / -d /g'
#certificates = subprocess.run(['certbot', 'certificates'],stdout=subprocess.PIPE)
#print(certificates)
#aux = os.system('ls -l | grep READ')
#print(aux)
#completed = subprocess.run(['certbot', '--expand','-d',WEB_DOMAIN,'--dry-run','-n','--apache','certonly'],stdout=subprocess.PIPE)
#completed = subprocess.run(['certbot', '--expand',arr,'--dry-run','-n', '--apache','certonly'],stdout=subprocess.PIPE)
#print(completed.stdout)



print(f'certbot --cert-name forums.achei.cl {WEB_DOMAIN} --dry-run --allow-subset-of-names certonly')