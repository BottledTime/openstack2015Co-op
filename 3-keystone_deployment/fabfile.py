from __future__ import with_statement
from fabric.decorators import with_settings
from fabric.api import *
from fabric.context_managers import cd
from fabric.colors import green, red, blue
import string
import subprocess
import logging

import sys
sys.path.append('..')
import env_config
from myLib import runCheck, createDatabaseScript, 
from myLib import keystone_check, database_check, align_y, align_n

######################## Configuring Environment ##############################

env.roledefs = env_config.roledefs
passwd = env_config.passwd

########################### Deployment ########################################

def setKeystoneConfigFile(admin_token,password):
    """
    Configure variables in keystone.conf
    """

    confFile= '/etc/keystone/keystone.conf'

    msg = 'Make a backup of keystone.conf'
    runCheck(msg, "cp {} {}.back12".format(confFile,confFile))

    crudiniCommands = "\n" 
    "crudini --set {} DEFAULT admin_token {}\n""".format(confFile,admin_token)
    "crudini --set {} DEFAULT verbose True\n".format(confFile)

    "crudini --set {} database connection ".format(confFile)
    "mysql://keystone:{}@controller/keystone\n".format(password)

    "crudini --set {} token provider "
    "keystone.token.providers.uuid.Provider\n".format(confFile)

    "crudini --set {} token driver ".format(confFile)
    "keystone.token.persistence.backends.sql.Token\n"

    "crudini --set {} revoke driver ".format(confFile)
    "keystone.contrib.revoke.backends.sql.Revoke\n"

    msg = 'Set up variables in {} using crudini'.format(confFile)
    runCheck(msg, crudiniCommands)

    # need to restart keystone so that it can read in the 
    # new admin_token from the configuration file
    msg = "Restart keystone service"
    runCheck(msg, "systemctl restart openstack-keystone.service")



def createGenericCertificatesAndKeys():
    """
    Set up Keystone's Public Key Infrastructure
    """
    msg = "Create a user and a group called 'keystone' for the PKI"
    runCheck(msg, "keystone-manage pki_setup --keystone-user keystone "
                  "--keystone-group keystone")

    msg = "Change ownership for /var/log/keystone and /etc/keystone/ssl"
    runCheck(msg, "chown -R keystone:keystone /var/log/keystone")
    runCheck(msg, "chown -R keystone:keystone /etc/keystone/ssl")

    msg = "Give rwx permissions to everyone on /etc/keystone/ssl"
    runCheck(msg, "chmod -R o-rwx /etc/keystone/ssl")

def configureCronToPurgeExpiredTokens():
    """
    Use cron to configure a periodic task that purges expired tokens hourly

    From the installation manual:
    "By default, the Identity service stores expired tokens in the database 
    indefinitely. The accumulation of expired tokens considerably increases
    the database size and might degrade service performance, particularly in 
    environments with limited resources."

    """
    msg = "Use cron to configure a periodic task "
          "that purges expired tokens hourly"
    runCheck(msg, "(crontab -l -u keystone 2>&1 | grep -q token_flush) || "
                  "echo '@hourly /usr/bin/keystone-manage token_flush "
                  ">/var/log/keystone/ keystone-tokenflush.log 2>&1' "
                  ">> /var/spool/cron/keystone")

def createUsersRolesAndTenants(admin_token):
    """
    Create (a) a user, a tenant, and role called 'admin', (b) a user and a 
    tenant called 'demo', (c) a tenant called 'service', and (d) a service 
    called 'keystone' and an endpoint fo this service, for Keystone's use
    """

    # get admin credentials
    credentials = "export OS_SERVICE_TOKEN={}; ".format(admin_token)
                  "export OS_SERVICE_ENDPOINT=http://controller:35357/v2.0; "

    with prefix(credentials):

        msg = "Create 'admin' tenant"
        runCheck(msg, "keystone tenant-create --name admin "
                      "--description 'Admin Tenant'")

        msg = "Create 'admin' user"
        runCheck(msg, "keystone user-create --name admin "
                      "--pass {} ".format(passwd['ADMIN_PASS'])
                      "--email {}" .format\
                        (env_config.keystone_emails['ADMIN_EMAIL']))

        msg = "Create 'admin' role"
        runCheck(msg, "keystone role-create --name admin")

        msg = "Give role 'admin' to user 'admin'"
        runCheck(msg, "keystone user-role-add --user admin "
                      "--tenant admin --role admin")


    
        msg = "Create 'demo' tenant"
        runCheck(msg, "keystone tenant-create --name demo "
                      "--description 'Demo Tenant'")

        msg = "Create 'demo' user"
        runCheck(msg, "keystone user-create --name demo --tenant demo "
                      "--pass {} ".format(passwd['DEMO_PASS'])
                      "--email {}".format\
                              (env_config.keystone_emails['DEMO_EMAIL'])) 



        msg = "Create 'service' tenant"
        runCheck(msg, "keystone tenant-create --name service "
                      "--description 'Service Tenant'")



        msg = "Create 'keystone' service"
        runCheck(msg, "keystone service-create --name keystone --type identity"
                      " --description 'OpenStack Identity'")

        msg = "Create an endpoint for the 'keystone' service"
        runCheck(msg, "keystone endpoint-create "
                      "--service-id "
                      "$(keystone service-list | "
                      "awk '/ identity / {print $2}') "
                      "--publicurl http://controller:5000/v2.0 "
                      "--internalurl http://controller:5000/v2.0 "
                      "--adminurl http://controller:35357/v2.0 "
                      "--region regionOne")


@roles('controller')
def installPackages():
    msg = 'Install packages'
    runCheck(msg, 'yum -y install openstack-keystone '
                  'python-keystoneclient',quiet=True)

    msg = "Start keystone service"
    runCheck(msg, "systemctl start openstack-keystone.service",quiet=True)

 
@roles('controller')
def setupKeystone():

    msg = "Restart MariaDB service"
    out = runCheck(msg, "systemctl restart mariadb")

    if out.return_code != 0:
        # we need mariadb working in order to proceed
        sys.exit("Failed to restart mariadb")

    # get Keystone database creation scripts
    databaseCreation = createDatabaseScript(\
            'keystone',passwd['KEYSTONE_DBPASS'])

    msg = "Create database for keystone"
    runCheck(msg, 'echo "' + databaseCreation + '" | mysql -u root')
    
    execute(installPackages)
  
    msg = "Generate an admin token"
    admin_token = runCheck(msg, 'openssl rand -hex 10')

    setKeystoneConfigFile(admin_token,passwd['KEYSTONE_DBPASS'])
    
    createGenericCertificatesAndKeys()

    msg = 'Populate the Identity service database'
    runCheck(msg, "su -s /bin/sh -c 'keystone-manage db_sync' keystone")

    # start and enable Identity service
    msg = "Enable keystone service"
    runCheck(msg, "systemctl enable openstack-keystone.service")
    msg = "Start keystone service"
    runCheck(msg, "systemctl start openstack-keystone.service")

    configureCronToPurgeExpiredTokens()

    createUsersRolesAndTenants(admin_token)


def deploy():
    execute(setupKeystone)

################################### TDD #######################################

@roles('controller')
def keystone_tdd():

    with settings(warn_only=True):

        keystone_check('keystone')
        database_check('keystone')

        # Check if 'admin' and 'demo' are users
        user_list_output = run("keystone --os-tenant-name admin "
                               "--os-username admin "
                               "--os-password {} ".format(passwd['ADMIN_PASS'])
                               " --os-auth-url http://controller:35357/v2.0 "
                               "user-list", quiet=True)

        if 'admin' in user_list_output:
            print align_y('Admin was found in user list')
        else:
            print align_n('admin not a user')

        if 'demo' in user_list_output:
            print align_y('Demo was found in user list')
        else:
            print align_n('demo not a user')

        # Check if 'admin', 'service' and 'demo' are tenants
        tenant_list_output = run("keystone --os-tenant-name admin "
                               "--os-username admin "
                               "--os-password {} ".format(passwd['ADMIN_PASS'])
                               " --os-auth-url http://controller:35357/v2.0 "
                               "tenant-list", quiet=True)

        for name in ['admin','demo','service']:
            if name in tenant_list_output:
                print align_y('{} was found in tenant list'.format(name))
            else:
                print align_n('{} not a tenant'.format(name))

        # Check if '_member_' and 'admin' are roles
        role_list_output = run("keystone --os-tenant-name admin "
                               "--os-username admin "
                               "--os-password {} ".format(passwd['ADMIN_PASS'])
                               " --os-auth-url http://controller:35357/v2.0 "
                               "role-list", quiet=True)
        
        if '_member_' in role_list_output:
            print align_y('_member_ is a role')
        else:
            print align_n('_member_ not a role')

        if 'admin' in role_list_output:
            print align_y('admin is a role')
        else:
            print align_n('admin not a role')

        # Check if non-admin user is forbidden to perform admin tasks
        user_list_output = run("keystone --os-tenant-name demo "
                               "--os-username demo "
                               "--os-password {} ".format(passwd['DEMO_PASS'])
                               " --os-auth-url http://controller:35357/v2.0 "
                               "user-list", quiet=True)

        if 'You are not authorized to perform the requested action' \
                in user_list_output:
            print align_y('demo was not allowed to run user-list')
        else:
            print align_n('demo was allowed to run user-list')

def tdd():
    print blue('Starting TDD function')
    execute(keystone_tdd)
    print blue('Done')

