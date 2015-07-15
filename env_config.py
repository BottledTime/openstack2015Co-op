import ConfigParser
import logging 
from subprocess import check_output, call
from fabric.api import run, sudo, env
from fabric.colors import red, green
from fabric.api import *

######################### Global variables ####################################

lslogs = ['/var/log/nova/nova-manage.log',
          '/var/log/nova/nova-api.log',
          '/var/log/heat/heat-manage.log',
          '/var/log/glance/api.log',
          '/var/log/nova/nova-novncproxy.log',
          '/var/log/nova/nova-consoleauth.log',
          '/var/log/nova/nova-api.log',
          '/var/log/keystone/keystone.log',
          '/var/log/heat/heat-api-cfn.log',
          '/var/log/heat/heat-api.log',
          '/var/log/neutron/server.log',
          '/var/log/nova/nova-conductor.log',
          '/var/log/heat/heat-manage.log',
          '/var/log/nova/nova-scheduler.log',
          '/var/log/rabbitmq/rabbit@localhost.log',
          '/tmp/test.log',
          '/var/log/heat/heat-engine.log',
          '/var/log/mariadb/server.log',
          '/var/log/rabbitmq/rabbit@localhost-sasl.log',
          '/var/log/nova/nova-cert.log',
          '/var/log/rabbitmq/rabbit@localhost.log',
          '/var/log/keystone/keystone-tokenflush.log',
          '/var/log/glance/registry.log',
          '/var/log/glusterfs/etc-glusterfs-glusterd.vol.log',
          ]

###############################################################################
#  ascii art generated from http://www.network-science.de/ascii/  Font = ogre 
'''
   ___               _            _   _             
  / _ \_ __ ___   __| |_   _  ___| |_(_) ___  _ __  
 / /_)/ '__/ _ \ / _` | | | |/ __| __| |/ _ \| '_ \ 
/ ___/| | | (_) | (_| | |_| | (__| |_| | (_) | | | |
\/    |_|  \___/ \__,_|\__,_|\___|\__|_|\___/|_| |_|
'''

if 'ipmi5' in check_output('echo $HOSTNAME',shell=True):
    # PRODUCTION
    roledefs = { 'compute' : ['root@compute1',
                                  'root@compute2',
                                  'root@compute3',
                                  'root@compute4',
                                  ],
                     'network' : ['root@network'],
#                     'storage' : ['root@storage'],
                     'controller' : ['root@controller']}

    roles = roledefs.keys()
    hosts = sum(roledefs.values(), [])


    logfilename='/opt/coop2015/coop2015/fabric.log'

    my_cnf="""
[mysqld]
datadir=/var/lib/mysql
socket=/var/lib/mysql/mysql.sock
# Disabling symbolic-links is recommended to prevent assorted security risks
symbolic-links=0
# Settings user and group are ignored when systemd is used.
# If you need to run mysqld under a different user or group,
# customize your systemd unit file for mariadb according to the
# instructions in http://fedoraproject.org/wiki/Systemd
bind-address = BIND_ADDRESS
default-storage-engine = innodb
innodb_file_per_table
collation-server = utf8_general_ci
init-connect = 'SET NAMES utf8'
character-set-server = utf8

[mysqld_safe]
log-error=/var/log/mariadb/mariadb.log
pid-file=/var/run/mariadb/mariadb.pid

#
# include all files from the config directory
#
!includedir /etc/my.cnf.d
           """
    # passwords
    passwd = {     'METADATA_SECRET' : '34m3t$3c43',
                   'ROOT_SECRET' : '34root43',
                   'RABBIT_PASS' : '34RabbGuest43',
                   'NOVA_DBPASS' : '34nova_db43',
                   'NEUTRON_DBPASS' : '34neu43',
                   'HEAT_DBPASS' : '34heat_db43',
                   'GLANCE_DBPASS' : '34glance_db43',
                   'SAHARA_DBPASS' : '34sahara_db43',
                   'CINDER_DBPASS' : '34cinder_db43',
                   'ADMIN_PASS' : '34adm43',
                   'DEMO_PASS' : '34demo43',
                   'KEYSTONE_DBPASS' : '34keydb43',
                   'NOVA_PASS' : '34nova_ks43',
                   'NEUTRON_PASS' : '34neu43',
                   'HEAT_PASS' : '34heat_ks43',
                   'GLANCE_PASS' : '34glance_ks43',
                   'SAHARA_PASS' : '34sahara_ks43',
                   'CINDER_PASS' : '34cinder_ks43',
                   'SWIFT_PASS' : '34Sw1f43',
                   'TROVE_PASS' : '34Tr0v343',
                   'TROVE_DBPASS' : '34Tr0v3db4s343'}

    partition = {   'size_reduction_of_home' : '3.5T',
                    'partition_size' : '1.5T',
                    #'glance_partition_size' : '300G',
                    #'cinder_partition_size' : '600G',
                    #'swift_partition_size' : '600G',
                    'stripe_number' : 3,
                    }

    nicDictionary = {
            'controller': { 
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.11',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'eno2',
                             'tnlIPADDR' : '192.168.2.11',
                             'tnlNETMASK' : '255.255.255.0',
                          },

            'network' : {
                             'mgtDEVICE' : 'enp2s0f0',
                             'mgtIPADDR' : '192.168.1.21',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'eno2',
                             'tnlIPADDR' : '192.168.2.21',
                             'tnlNETMASK' : '255.255.255.0',
                             'extDEVICE' : 'enp2s0f1',
                             'extTYPE' : 'Ethernet',
                             'extONBOOT' : '"yes"',
                             'extBOOTPROTO' : '"none"',
                             'extIPADDR' : '192.168.3.21',
                        },

            'compute1' : {
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.41',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'eno2',
                             'tnlIPADDR' : '192.168.2.41',
                             'tnlNETMASK' : '255.255.255.0',
                         },

            'compute2' : {
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.42',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'eno2',
                             'tnlIPADDR' : '192.168.2.42',
                             'tnlNETMASK' : '255.255.255.0',
                         },

            'compute3' : {
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.43',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'eno2',
                             'tnlIPADDR' : '192.168.2.43',
                             'tnlNETMASK' : '255.255.255.0',
                         },

            'compute4' : {
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.44',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'eno2',
                             'tnlIPADDR' : '192.168.2.44',
                             'tnlNETMASK' : '255.255.255.0',
                         },

            'storage1' : {
                             'mgtDEVICE' : 'enp0s25',
                             'mgtIPADDR' : '192.168.1.31',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                         },

            }
    """
     _____                        _                   
    |___ /     /\ /\___ _   _ ___| |_ ___  _ __   ___ 
      |_ \    / //_/ _ \ | | / __| __/ _ \| '_ \ / _ \
     ___) |  / __ \  __/ |_| \__ \ || (_) | | | |  __/
    |____/   \/  \/\___|\__, |___/\__\___/|_| |_|\___|
                        |___/   
    """


    keystone_emails = { 'ADMIN_EMAIL' : 'admin@example.com',
                         'DEMO_EMAIL' : 'demo@example.com'}



    admin_openrc = "export OS_TENANT_NAME=admin; " +\
            "export OS_USERNAME=admin; " + \
            "export OS_PASSWORD={}; ".format(passwd['ADMIN_PASS']) + \
            "export OS_AUTH_URL=http://controller:35357/v2.0"

    demo_openrc = "export OS_TENANT_NAME=demo; " +\
            "export OS_USERNAME=demo; " + \
            "export OS_PASSWORD={}; ".format(passwd['DEMO_PASS']) + \
            "export OS_AUTH_URL=http://controller:5000/v2.0"

    '''
     _  _       ___ _                      
    | || |     / _ \ | __ _ _ __   ___ ___ 
    | || |_   / /_\/ |/ _` | '_ \ / __/ _ \
    |__   _| / /_\\| | (_| | | | | (_|  __/
       |_|   \____/|_|\__,_|_| |_|\___\___|
    '''

    glanceGlusterBrick = '/mnt/gluster/glance_volume/glance/images'
    novaGlusterBrick = '/mnt/gluster/glance_volume/instance'


    '''
      __         __           _                   
     / /_     /\ \ \___ _   _| |_ _ __ ___  _ __  
    | '_ \   /  \/ / _ \ | | | __| '__/ _ \| '_ \ 
    | (_) | / /\  /  __/ |_| | |_| | | (_) | | | |
     \___/  \_\ \/ \___|\__,_|\__|_|  \___/|_| |_|
                                              
    '''

    # Specifications for the initial networks

    ext_subnet = {
            'start' : '192.168.1.100',
            'end' : '192.168.1.150',
            'gateway' : '192.168.1.1',
            'cidr' : '192.168.1.0/24',
            }

    demo_subnet = {
            'gateway' : '10.0.0.1', 
            'cidr' : '10.0.0.0/8', 
            }



##############################################################################

########  ######## ##     ## 
##     ## ##       ##     ## 
##     ## ##       ##     ## 
##     ## ######   ##     ## 
##     ## ##        ##   ##  
##     ## ##         ## ##   
########  ########    ###    

##############################################################################

else:
    # DEVELOPMENT

    # logging
    logfilename = '/tmp/test.log'


    my_cnf="""
[mysqld]
datadir=/var/lib/mysql
socket=/var/lib/mysql/mysql.sock
# Disabling symbolic-links is recommended to prevent assorted security risks
symbolic-links=0
# Settings user and group are ignored when systemd is used.
# If you need to run mysqld under a different user or group,
# customize your systemd unit file for mariadb according to the
# instructions in http://fedoraproject.org/wiki/Systemd
bind-address = BIND_ADDRESS
default-storage-engine = innodb
innodb_file_per_table
collation-server = utf8_general_ci
init-connect = 'SET NAMES utf8'
character-set-server = utf8

[mysqld_safe]
log-error=/var/log/mariadb/mariadb.log
pid-file=/var/run/mariadb/mariadb.pid

#
# include all files from the config directory
#
!includedir /etc/my.cnf.d
           """
    # for the env dictionary
    roledefs = { 'compute' : ['root@compute1'],
                 'network' : ['root@network'],
                 # 'storage' : ['root@storage1'],
                 'storage' : [],
                 'controller' : ['root@controller']}

    roles = roledefs.keys()
    hosts = sum(roledefs.values(), [])

    # ntp
    ntpServers = ['time1.srv.ualberta.ca',
                  'time2.srv.ualberta.ca',
                  'time3.srv.ualberta.ca',
                  ]

    # passwords
    passwd = { 'METADATA_SECRET' : '34m3t$3c43',
               'ROOT_SECRET' : '34root43',
               'RABBIT_PASS' : '34RabbGuest43',
               'NEUTRON_DBPASS' : '34neu43',
               'HEAT_DBPASS' : '34heat_db43',
               'GLANCE_PASS' : '34glance_ks43',
               'GLANCE_DBPASS' : '34glance_db43',
               'SAHARA_DBPASS' : '34sahara_db43',
               'CINDER_DBPASS' : '34cinder_db43',
               'ADMIN_PASS' : '34adm43',
               'DEMO_PASS' : '34demo43',
               'KEYSTONE_DBPASS' : '34keydb43',
               'NOVA_PASS' : '34nova_ks43',
               'NOVA_DBPASS' : '34nova_db43',
               'NEUTRON_PASS' : '34neu43',
               'HEAT_PASS' : '34heat_ks43',
               'SAHARA_PASS' : '34sahara_ks43',
               'CINDER_PASS' : '34cinder_ks43',
               'SWIFT_PASS' : '34Sw1f43',
               'TROVE_PASS' : '34Tr0v343',
               'TROVE_DBPASS' : '34Tr0v3db4s343',
               'CEILOMETER_PASS' : '34ceilometer_db43',
               }


    ###########################################################################

    ##    ## ######## ######## ##      ##  #######  ########  ##    ## 
    ###   ## ##          ##    ##  ##  ## ##     ## ##     ## ##   ##  
    ####  ## ##          ##    ##  ##  ## ##     ## ##     ## ##  ##   
    ## ## ## ######      ##    ##  ##  ## ##     ## ########  #####    
    ##  #### ##          ##    ##  ##  ## ##     ## ##   ##   ##  ##   
    ##   ### ##          ##    ##  ##  ## ##     ## ##    ##  ##   ##  
    ##    ## ########    ##     ###  ###   #######  ##     ## ##    ## 

    ###########################################################################

    nicDictionary = {
            'controller': { 
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.11',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'enp2s10',
                             'tnlIPADDR' : '192.168.2.11',
                             'tnlNETMASK' : '255.255.255.0',
                          },

            'network' : {
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.21',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'enp2s10',
                             'tnlIPADDR' : '192.168.2.21',
                             'tnlNETMASK' : '255.255.255.0',
                             'extDEVICE' : 'enp2s12',
                             'extTYPE' : 'Ethernet',
                             'extONBOOT' : '"yes"',
                             'extBOOTPROTO' : '"none"',
                             'extIPADDR' : '192.168.3.21',
                        },

            'compute1' : {
                             'mgtDEVICE' : 'eno1',
                             'mgtIPADDR' : '192.168.1.41',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                             'tnlDEVICE' : 'enp2s10',
                             'tnlIPADDR' : '192.168.2.41',
                             'tnlNETMASK' : '255.255.255.0',
                         },

            'storage1' : {
                             'mgtDEVICE' : 'enp0s25',
                             'mgtIPADDR' : '192.168.1.31',
                             'mgtNETMASK' : '255.255.255.0',
                             'mgtGATEWAY' : '192.168.1.1',
                             'mgtDNS1' : '129.128.208.13',
                         },

            }

    # admin-openrc and demo-openrc
    
    # These scripts set up credentials for the keystone users
    # admin and demo respectively. They export system variables that 
    # allow the user to execute certain keystone CLI commands. They 
    # are necessary every time the deployment scripts use keystone.

    admin_openrc = "export OS_TENANT_NAME=admin; " +\
            "export OS_USERNAME=admin; " + \
            "export OS_PASSWORD={}; ".format(passwd['ADMIN_PASS']) + \
            "export OS_AUTH_URL=http://controller:35357/v2.0"

    demo_openrc = "export OS_TENANT_NAME=demo; " +\
            "export OS_USERNAME=demo; " + \
            "export OS_PASSWORD={}; ".format(passwd['DEMO_PASS']) + \
            "export OS_AUTH_URL=http://controller:5000/v2.0"

    ###########################################################################

    ##    ## ######## ##    ##  ######  ########  #######  ##    ## ######## 
    ##   ##  ##        ##  ##  ##    ##    ##    ##     ## ###   ## ##       
    ##  ##   ##         ####   ##          ##    ##     ## ####  ## ##       
    #####    ######      ##     ######     ##    ##     ## ## ## ## ######   
    ##  ##   ##          ##          ##    ##    ##     ## ##  #### ##       
    ##   ##  ##          ##    ##    ##    ##    ##     ## ##   ### ##       
    ##    ## ########    ##     ######     ##     #######  ##    ## ######## 

    ###########################################################################


    keystone_emails = { 'ADMIN_EMAIL' : 'admin@example.com',
                         'DEMO_EMAIL' : 'demo@example.com'}



    ###########################################################################

    ##    ## ######## ##     ## ######## ########   #######  ##    ## 
    ###   ## ##       ##     ##    ##    ##     ## ##     ## ###   ## 
    ####  ## ##       ##     ##    ##    ##     ## ##     ## ####  ## 
    ## ## ## ######   ##     ##    ##    ########  ##     ## ## ## ## 
    ##  #### ##       ##     ##    ##    ##   ##   ##     ## ##  #### 
    ##   ### ##       ##     ##    ##    ##    ##  ##     ## ##   ### 
    ##    ## ########  #######     ##    ##     ##  #######  ##    ## 
    ############################################################################

    # Specifications for the initial networks

    ext_subnet = {
            'start' : '192.168.1.100',
            'end' : '192.168.1.150',
            'gateway' : '192.168.1.1',
            'cidr' : '192.168.1.0/24',
            }

    demo_subnet = {
            'gateway' : '10.0.0.1', 
            'cidr' : '10.0.0.0/8', 
            }



    ###########################################################################

     ######  ########  #######  ########     ###     ######   ######## 
    ##    ##    ##    ##     ## ##     ##   ## ##   ##    ##  ##       
    ##          ##    ##     ## ##     ##  ##   ##  ##        ##       
     ######     ##    ##     ## ########  ##     ## ##   #### ######   
          ##    ##    ##     ## ##   ##   ######### ##    ##  ##       
    ##    ##    ##    ##     ## ##    ##  ##     ## ##    ##  ##       
     ######     ##     #######  ##     ## ##     ##  ######   ######## 

    ###########################################################################

    partition = {   'size_reduction_of_home' : '350G',
                    'partition_size' : '350G',
                    #'glance_partition_size' : '30G',
                    #'cinder_partition_size' : '60G',
                    #'swift_partition_size' : '60G',
                    'stripe_number' : 1,
                    }

    cinderGlusterDir = '/mnt/gluster/cinder'

    ##########################################################################

         ######   ##       ##     ##  ######  ######## ######## ########  
        ##    ##  ##       ##     ## ##    ##    ##    ##       ##     ## 
        ##        ##       ##     ## ##          ##    ##       ##     ## 
        ##   #### ##       ##     ##  ######     ##    ######   ########  
        ##    ##  ##       ##     ##       ##    ##    ##       ##   ##   
        ##    ##  ##       ##     ## ##    ##    ##    ##       ##    ##  
         ######   ########  #######   ######     ##    ######## ##     ## 

    ##########################################################################

    glusterPath = '/mnt/gluster/'

    volume = 'gluster_volume'
    brick = 'brick'
    partitionName = 'storage'

    glanceVolume = 'glance_volume'
    glanceBrick = 'glance_brick'
    glancePartition = 'strFile'

    cinderVolume = 'cinder_volume'
    cinderBrick = 'cinder_brick'
    cinderPartition = 'strBlk'

    swiftVolume = 'swift_volume'
    swiftBrick = 'swift_brick'
    swiftPartition = 'strObj'


    ##################################################################

              #####  #          #    #     #  #####  ####### 
             #     # #         # #   ##    # #     # #       
             #       #        #   #  # #   # #       #       
             #  #### #       #     # #  #  # #       #####   
             #     # #       ####### #   # # #       #       
             #     # #       #     # #    ## #     # #       
              #####  ####### #     # #     #  #####  ####### 

    ##################################################################

    glanceGlusterDir = '/mnt/gluster/glance/images'
    novaGlusterDir = '/mnt/gluster/instance'

    ##################################################################

              ######  ##      ## #### ######## ######## 
             ##    ## ##  ##  ##  ##  ##          ##    
             ##       ##  ##  ##  ##  ##          ##    
              ######  ##  ##  ##  ##  ######      ##    
                   ## ##  ##  ##  ##  ##          ##    
             ##    ## ##  ##  ##  ##  ##          ##    
              ######   ###  ###  #### ##          ##    

    ##################################################################

    # Find out how to get decent hash values
    hashPathPrefix = '3443'
    hashPathSuffix = '3443'

    swiftGlusterDir = '/mnt/gluster/swift'
    # base rsyncd.conf
    # MANAGEMENT_INTERFACE_IP_ADDRESS and PATH will be replaced by adequate
    # values in the deployment script

    rsyncd_conf = """
uid = swift
gid = swift
log file = /var/log/rsyncd.log
pid file = /var/run/rsyncd.pid
address = MANAGEMENT_INTERFACE_IP_ADDRESS

[account]
max connections = 2
path = PATH
read only = false
lock file = /var/lock/account.lock

[container]
max connections = 2
path = PATH
read only = false
lock file = /var/lock/container.lock

[object]
max connections = 2
path = PATH
read only = false
lock file = /var/lock/object.lock
"""


    ##################################################################


     ######  ######## #### ##        #######  ##     ## ######## ######## ######## ########  
    ##    ## ##        ##  ##       ##     ## ###   ### ##          ##    ##       ##     ## 
    ##       ##        ##  ##       ##     ## #### #### ##          ##    ##       ##     ## 
    ##       ######    ##  ##       ##     ## ## ### ## ######      ##    ######   ########  
    ##       ##        ##  ##       ##     ## ##     ## ##          ##    ##       ##   ##   
    ##    ## ##        ##  ##       ##     ## ##     ## ##          ##    ##       ##    ##  
     ######  ######## #### ########  #######  ##     ## ########    ##    ######## ##     ## 

    ##################################################################


    metering_secret = "34m43s34m43"





# ref: ascii art generated from: 
# 1) http://www.desmoulins.fr/index_us.php?pg=scripts!online!asciiart
# 2) http://patorjk.com/software/taag/#p=display&h=3&v=1&f=Banner3&t=Basic%20Networking
