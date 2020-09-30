#!/usr/bin/env python3
#import pdb; pdb.set_trace()
import os
import sys
import shutil
import argparse
import subprocess
from datetime import datetime
from pwd import getpwnam  

#https://docs.python.org/3.3/library/argparse.html#nargs

parser = argparse.ArgumentParser(description='Deinput_filees a new domain in Sympa.')
#parser.add_argument('integers', metavar='N', type=int, nargs='+', help='an integer for the accumulator')
parser.add_argument('--action',"-a", required=True, help='Action to be executed by the script', choices=['add', 'remove'])
parser.add_argument('--web',"-w", required=True, help='Domain used to access the web interface')
parser.add_argument('--mail',"-m", required=True, help='Domain used for mails')
parser.add_argument('--title',"-t", help='The name of your mailing list service', default="Your MailingLists Service")
parser.add_argument('--lang', help='Language for the user interface', default="en_US")
parser.add_argument('--listmasters', help='Listmasters email addresses separated by commas')
args = parser.parse_args()

SYMPA_CONF = '/etc/apache2/sites-available/sympa.conf'
SYMPA_LE_SSL_CONF = '/etc/apache2/sites-available/sympa-le-ssl.conf'
DOMINIOS_VIRTUALES = '/etc/exim4/dominios_virtuales'
# setup
MX_DOMAIN = args.mail
WEB_DOMAIN = args.web
SYSCONFDIR = '/etc/sympa/'
BACKUPS_DIR = 'domain_manager_backups'
DEFAULT_LANG=args.lang
TITLE=args.title
if (args.listmasters is not None):
    ROBOT_LISTMASTERS = "listmaster " + args.listmasters
else:
    ROBOT_LISTMASTERS = ""

os.makedirs(BACKUPS_DIR, exist_ok=True)
action = args.action
sympa_pl = '/usr/lib/sympa/bin/sympa.pl'

def validate_dns():    
    mx_record = subprocess.run(['dig', '+short','MX',MX_DOMAIN],stdout=subprocess.PIPE).stdout.decode('ascii').strip('\n')
    cname_record = subprocess.run(['dig', '+short','CNAME',MX_DOMAIN],stdout=subprocess.PIPE).stdout.decode('ascii').strip('\n')
    #txt_records = subprocess.run(['dig', '+short','MX',MX_DOMAIN],stdout=subprocess.PIPE).stdout.decode('ascii').split('\n')
    if mx_record == '' or cname_record == '':
        print('Configure your DNS ')
        return False
    else:
        return True

def add_exim_conf():
    dominios_virtuales = open('/etc/exim4/dominios_virtuales', 'a')
    dominios_virtuales.write("\n" + MX_DOMAIN)
    dominios_virtuales.close()
    print('service exim4 restart')

def remove_exim_conf():
    with open(DOMINIOS_VIRTUALES, "r") as file:
        lines = file.readlines()
    with open(DOMINIOS_VIRTUALES, "w") as file:
        for line in lines:
            if (line.strip("\n") != MX_DOMAIN):
                file.write(line)
    print('service exim4 restart')

def conf_check(cmd, arg):
    try:
        subprocess.run([cmd, arg],stdout=subprocess.PIPE,stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as err:
        print('ERROR:', err)
        restore_backup()
        exit()
        return False
    else:
        #print('returncode:', completed.returncode)
        return True

def add_sympa_conf():

    # #Importante: este archivo o carpeta tiene que estar con permisos sympa:sympa
    # mkdir /etc/sympa/MX_DOMAIN
    list_dir = SYSCONFDIR + MX_DOMAIN + '/'

    # cp /etc/sympa/robot.conf.EXAMPLE /etc/sympa/MX_DOMAIN/robot.conf
    os.makedirs(list_dir, exist_ok=True)

    # src = SYSCONFDIR + 'robot.conf.EXAMPLE'
    src = 'templates/sympa/robot.conf.EXAMPLE'
    robot_conf = list_dir + 'robot.conf'
    open(robot_conf, 'a').close()

    # nano /etc/sympa/MX_DOMAIN/robot.conf # Modificar las siguientes variables.
    # # http_host=WEB_DOMAIN
    # # wwsympa_url=http://WEB_DOMAIN
    # # domain=MX_DOMAIN

    append_and_replace(src, robot_conf)

    shutil.chown(list_dir, 'sympa', 'sympa')  
    shutil.chown(robot_conf, 'sympa', 'sympa')  

    # mkdir /var/log/apache2/virtuales/MX_DOMAIN
    # chown root:adm /var/log/apache2/virtuales/MX_DOMAIN
    var_log = "/var/log/apache2/virtuales/"+MX_DOMAIN
    os.makedirs(var_log, exist_ok=True)
    shutil.chown(var_log, 'root', 'adm')  

    # mkdir /var/lib/sympa/list_data/MX_DOMAIN
    # chown -R sympa:sympa /var/lib/sympa/list_data/MX_DOMAIN
    list_data = "/var/lib/sympa/list_data/"+MX_DOMAIN
    os.makedirs(list_data, exist_ok=True)
    shutil.chown(list_data, 'sympa', 'sympa')  

    # print(os.listdir('./'))
    # print(pydig.query('forums.rio20.net', 'MX'))

    #chequeo configuración de sympa
    conf_check(sympa_pl,"--health_check")
    print(f"The configuration for {WEB_DOMAIN} has been added in Sympa")


def remove_sympa_conf():
    list_dir = SYSCONFDIR + MX_DOMAIN + '/'
    robot_conf = list_dir + 'robot.conf'
    conf_check(sympa_pl,"--health_check")
    os.remove(robot_conf)
    os.rmdir(list_dir)
    print(f"Sympa configuration for {MX_DOMAIN} has been deleted.")
    return True

def add_ssl_conf():
    cmd = "certbot certificates | grep Domains: | sed 's/    Domains://g'  | sed 's/ / -d /g'"
    certificates = ' -d '+ WEB_DOMAIN + subprocess.check_output(cmd, shell=True).decode('UTF-8')
    os.system(f'certbot --cert-name forums.achei.cl {certificates} --dry-run certonly')
    return True

def remove_ssl_conf():
    cmd = f"certbot certificates | grep Domains: | sed 's/    Domains://g'  | sed 's/ {WEB_DOMAIN}//g' |sed 's/ / -d /g'"
    certificates = subprocess.check_output(cmd, shell=True).decode('UTF-8')
    os.system(f'certbot --cert-name forums.achei.cl {certificates} --dry-run certonly')
    return True

def tmp_backup():
    if os.path.isfile(SYMPA_CONF):
        shutil.copy(SYMPA_CONF, '/tmp/sympa.conf.bk')
    if os.path.isfile(SYMPA_LE_SSL_CONF):
        shutil.copy(SYMPA_LE_SSL_CONF, '/tmp/sympa-le-ssl.conf.bk')
    if os.path.isfile('/etc/exim4/dominios_virtuales'):
        shutil.copy('/etc/exim4/dominios_virtuales', '/tmp/dominios_virtuales.bk')
    # backup de robot.conf

def do_backup():
    now = datetime.now().strftime("%Y-%m-%d_%H.%M")
    os.makedirs(BACKUPS_DIR + 'etc/apache2/sites-available/', exist_ok=True)
    os.makedirs(BACKUPS_DIR + 'etc/exim4/', exist_ok=True)
    if os.path.isfile('/tmp/sympa.conf.bk'):
        shutil.copy('/tmp/sympa.conf.bk',BACKUPS_DIR+'etc/apache2/sites-available/sympa.conf_'+now)
    if os.path.isfile('/tmp/sympa-le-ssl.conf.bk'):
        shutil.copy('/tmp/sympa-le-ssl.conf.bk',BACKUPS_DIR+'etc/apache2/sites-available/sympa-le-ssl.conf_'+now)
    if os.path.isfile('/tmp/dominios_virtuales.bk'):
        shutil.copy('/tmp/dominios_virtuales.bk', BACKUPS_DIR+'etc/exim4/dominios_virtuales_'+now)
    print("Backup file have been created in "+BACKUPS_DIR+'etc/apache2/sites-available/sympa.conf_'+now)


def restore_backup():
    log_dir = "/var/log/apache2/virtuales/"+MX_DOMAIN
    os.rmdir(log_dir)
    list_dir = SYSCONFDIR + MX_DOMAIN + '/'
    shutil.rmtree(list_dir)
    if os.path.isfile('/tmp/sympa.conf.bk'):
        shutil.copy('/etc/apache2/sites-available/sympa.conf',"/tmp/roto")
        shutil.copy('/tmp/sympa.conf.bk', '/etc/apache2/sites-available/sympa.conf')
    if os.path.isfile('/tmp/sympa-le-ssl.conf.bk'):
        shutil.copy('/tmp/sympa-le-ssl.conf.bk', '/etc/apache2/sites-available/sympa-le-ssl.conf')
    print("No changes were made")
        

def add_apache_conf():
    src = 'templates/new-domain.conf'
    dest = '/etc/apache2/sites-available/sympa.conf'
    append_and_replace(src, dest)

#   src = 'templates/new-domain-ssl.conf'
#   dest = '/etc/apache2/sites-available/sympa-le-ssl.conf'
#   append_and_replace(src, dest)

    # mkdir /var/log/apache2/virtuales/MX_DOMAIN
    log_dir = "/var/log/apache2/virtuales/"+MX_DOMAIN
    os.makedirs(log_dir, exist_ok=True)

    conf_check("apachectl","-t")
    print(f"A VirtualHost has been added in /etc/apache2/sites-available/sympa.conf for {WEB_DOMAIN}")
    return True

def append_and_replace(src, dest):
    src_file = open(src, "r")
    dest_file = open(dest, "a+")
    lines_to_append = src_file.readlines()

    with dest_file as file_object:
        for line in lines_to_append:
            if "WEB_DOMAIN" in line :
                line = line.replace("WEB_DOMAIN",WEB_DOMAIN)
            elif "MX_DOMAIN" in line :
                line = line.replace("MX_DOMAIN",MX_DOMAIN)                
            elif "DEFAULT_LANG" in line :
                line = line.replace("DEFAULT_LANG",DEFAULT_LANG)                
            elif "ROBOT_LISTMASTERS" in line :
                line = line.replace("ROBOT_LISTMASTERS",ROBOT_LISTMASTERS)                
            elif "TITLE" in line :
                line = line.replace("TITLE",TITLE)                
            file_object.write(line)

    src_file.close()
    dest_file.close()
    return True

def exist_domain():
    exist = os.path.isfile(SYSCONFDIR + MX_DOMAIN + '/robot.conf')
    return exist

def add():
    if(not exist_domain()):
        validate_dns()
        add_exim_conf()
        add_sympa_conf()
        add_ssl_conf()
        add_apache_conf()
        do_backup()
    else:
        print(WEB_DOMAIN,"is already configured in Sympa\nNo changes were made")

def main(action):
    # Get the function from switcher dictionary
    func = switcher.get(action, invalid_action)
    # Execute the function
    return func()


def remove_apache_conf():
    with open(SYMPA_CONF, "r") as file:
        lines = file.readlines()
    with open(SYMPA_CONF, "w") as file:
        write = True
        for line in lines:
            if (write and line.strip("\n") != f"# START {WEB_DOMAIN}"):
                file.write(line)
            elif (line.strip("\n") == f"# START {WEB_DOMAIN}"):
                write = False
            elif (line.strip("\n") == f"# END {WEB_DOMAIN}"):
                write = True

    conf_check("apachectl","-t")
    return True

def remove():
    if(exist_domain()):
        remove_exim_conf()
        remove_sympa_conf()
        remove_ssl_conf()
        remove_apache_conf()
        do_backup()
    else:
        print(WEB_DOMAIN,"does not exist in Sympa.\nNo changes were made")

def invalid_action():
    print("Invalid action: ", action)

switcher = {
        'add': add,
        'remove': remove,
    }

tmp_backup()
main(action)