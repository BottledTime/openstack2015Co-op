from __future__ import with_statement
from fabric.api import *
from fabric.colors import green, red, blue
import string
import logging
import time

import sys
sys.path.append('..')
import env_config
from myLib import runCheck, set_parameter, checkLog
from myLib import align_y, align_n, keystone_check, database_check, saveConfigFile


############################ Config ########################################

env.roledefs = env_config.roledefs
passwd = env_config.passwd

ml2_conf_file = '/etc/neutron/plugins/ml2/ml2_conf.ini.test'
l3_agent_file = '/etc/neutron/l3_agent.ini.test'
dhcp_agent_file = '/etc/neutron/dhcp_agent.ini.test'

# dict mapping VLAN tags to CIDRs
vlans = {
        208: '129.128.208.0/24',
        209: '129.128.209.0/24',
        6: '142.244.63.0/24',
        2131: '129.128.213.0/24',
        }

# name for the test tenant that is used in this script
tenant = 'test-vlan'

# use the test tenant in the credentials
credentials = env_config.admin_openrc.replace('OS_TENANT_NAME=admin','OS_TENANT_NAME=%s' % tenant)

############################# General ####################################

@roles('controller')
def backupConfFile(confFile):

    backupFile = confFile + '.bak'

    exists = run('[ -e %s ]' % backupFile, warn_only=True).return_code == 0

    if exists:
        print blue('Backup file already exists and will not be rewritten')
    else:
        msg = 'Make backup file'
        runCheck(msg, 'cp %s %s' % (confFile, backupFile))

############################# VxLAN setup ################################

@roles('network', 'compute')
def VxLANBasicSetup():
    "Create and set up two bridges for the VxLAN"
    # Reference: http://www.opencloudblog.com/?p=614 

    msg = 'Create br-uplink bridge'
    runCheck(msg, 'ovs-vsctl add-br br-uplink')

    msg = 'Create br-vlan bridge'
    runCheck(msg, 'ovs-vsctl add-br br-vlan')

    physicalInterface = env_config.nicDictionary[env.host]['tnlDEVICE']

    msg = 'Add the physical interface as the uplink'
    runCheck(msg, 'ip link set dev %s up' % physicalInterface)

    # Increase MTU so make room for the VXLAN headers
    # How to set up switch?
    msg = 'Increase MTU on the uplink'
    runCheck(msg, 'ip link set dev %s mtu 1600' % physicalInterface)

    msg = 'Add a port from br-uplink to the physical interface'
    trunk = ",".join([str(tag) for tag in vlans.keys()])
    runCheck(msg, 'ovs-vsctl add-port br-uplink %s ' % physicalInterface + \
            '-- set port %s vlan_mode=trunk trunk=%s' % trunk)


    msg = 'Create a patch port from br-uplink to br-vlan'
    runCheck(msg, 'ovs-vsctl add-port br-uplink patch-to-vlan '
            '-- set Interface patch-to-vlan type=patch options:peer=patch-to-uplink')

    msg = 'Create a patch port from br-vlan to br-uplink'
    runCheck(msg, 'ovs-vsctl add-port br-vlan patch-to-uplink '
            '-- set Interface patch-to-uplink type=patch options:peer=patch-to-vlan')

    # create the Linux IP interface required for VXLAN transport
    # this interface is attached to vlan 4000 of br-uplink
    
    # Apparently unnecessary

    # msg = 'Attach device l3vxlan to br-uplink'
    # runCheck(msg, 'ovs-vsctl add-port br-uplink l3vxlan tag=4000 '
    #         '-- set Interface l3vxlan type=internal')
    # msg = 'Add IP to the l3vxlan'
    # runCheck(msg, 'ip addr add %s dev l3vxlan' % l3vxlanIP)
    # msg = 'Set l3vlan up'
    # runCheck(msg, 'ip link set dev l3vxlan up')
    # msg = 'Increase MTU for l3vxlan'
    # runCheck(msg, 'ip link set dev l3vxlan mtu 1600')

@roles('network', 'compute')
def VxLANSetMl2Conf():
    # Reference: http://www.opencloudblog.com/?p=630

    confFile = ml2_conf_file
    
    backupConfFile(confFile)

    vniRanges = '65537:69999'
    networkVlanRanges = 'external:6:2131' 

    set_parameter(confFile, 'ml2', 'type_drivers', 'vxlan,local,vlan,flat')
    set_parameter(confFile, 'ml2', 'tenant_network_types', 'vxlan')
    set_parameter(confFile, 'ml2',  'mechanism_drivers', 'openvswitch')
     
    set_parameter(confFile, 'ml2_type_vxlan', 'vni_ranges', vniRanges)
      
    set_parameter(confFile, 'ml2_type_vlan', 'network_vlan_ranges', networkVlanRanges)
       
    set_parameter(confFile, 'ml2_type_flat', 'flat_networks', '*')
        
    set_parameter(confFile, 'ovs', 'bridge_mappings', 'vlannet:br-vlan')
    set_parameter(confFile, 'ovs', 'tunnel_type', 'vxlan')
    set_parameter(confFile, 'ovs', 'tunnel_bridge' , 'br-tun')
    set_parameter(confFile, 'ovs', 'integration_bridge' , 'br-int')
    set_parameter(confFile, 'ovs', 'tunnel_id_ranges' , vniRanges)
    set_parameter(confFile, 'ovs', 'enable_tunneling' , 'True')
    set_parameter(confFile, 'ovs', 'tenant_network_type' , 'vxlan')
    # set_parameter(confFile, 'ovs', 'local_ip' , l3vxlanIP)
    set_parameter(confFile, 'ovs', 'local_ip' , 
            env_config.nicDictionary[env.host]['tnlIPADDR'])
         
    set_parameter(confFile, 'agent', 'tunnel_types' , 'vxlan')
    set_parameter(confFile, 'agent', 'l2_population' , 'False')

@roles('network', 'compute')
def VxLANSetL3Conf():
    # Reference: http://www.opencloudblog.com/?p=630

    confFile = l3_agent_file
    backupConfFile(confFile)


    # very important - set the two following entries to an empty string
    # do not leave the default values
    set_parameter(confFile, 'DEFAULT', 'gateway_external_network_id', '')
    set_parameter(confFile, 'DEFAULT', 'external_network_bridge', '')

    # we use the legacy mode - HA and DVR are broken in Juno and should 
    # not used in production environments
    set_parameter(confFile, 'DEFAULT', 'agent_mode', 'legacy')
    
    # nova metadata is deployed only on the network node(s) and listens on controller node
    set_parameter(confFile, 'DEFAULT', 'metadata_port', '8775')
    set_parameter(confFile, 'DEFAULT', 'metadata_ip', 'controller')
    set_parameter(confFile, 'DEFAULT', 'enable_metadata_proxy', 'True')
    
    set_parameter(confFile, 'DEFAULT', 'handle_internal_only_routers', 'true')
    set_parameter(confFile, 'DEFAULT', 'router_delete_namespaces', 'True')
    
    # veths should be avoided
    set_parameter(confFile, 'DEFAULT', 'ovs_use_veth', 'false')
    
    set_parameter(confFile, 'DEFAULT', 'interface_driver', 
            'neutron.agent.linux.interface.OVSInterfaceDriver')
    set_parameter(confFile, 'DEFAULT', 'use_namespaces', 'true')

@roles('network', 'compute')
def VxLANSetDHCPConf():
    # Reference: http://www.opencloudblog.com/?p=630

    confFile = dhcp_agent_file
    backupConfFile(confFile)

    set_parameter(confFile, 'DEFAULT', 'dhcp_delete_namespaces', 'True')
    set_parameter(confFile, 'DEFAULT', 'enable_metadata_network', 'false')
    set_parameter(confFile, 'DEFAULT', 'enable_isolated_metadata', 'true')
    set_parameter(confFile, 'DEFAULT', 'use_namespaces', 'true')
    set_parameter(confFile, 'DEFAULT', 'dhcp_driver', 'neutron.agent.linux.dhcp.Dnsmasq')
    set_parameter(confFile, 'DEFAULT', 'ovs_use_veth', 'false')
    set_parameter(confFile, 'DEFAULT', 'interface_driver', 
            'neutron.agent.linux.interface.OVSInterfaceDriver')
    set_parameter(confFile, 'DEFAULT', 'dhcp_agent_manager', 
            'neutron.agent.dhcp_agent.DhcpAgentWithStateReport')

@roles('controller')
def setUpVxLAN():

    # execute(VxLANBasicSetup)
    execute(VxLANSetMl2Conf)
    execute(VxLANSetL3Conf)
    execute(VxLANSetDHCPConf)

    msg = 'Restart neutron server'
    runCheck(msg, 'systemctl restart neutron-server.service')

################################### InitialVlans ####################################

@roles('controller')
def VLAN_createTenant():
    "Create a tenant to test VLANs"

    with prefix(env_config.admin_openrc):

        tenantList = run('keystone tenant-list')
        if tenant in tenantList:
            print blue("Tenant already created. Nothing done")
        else:
            msg = 'Create tenant ' + tenant
            runCheck(msg, 'keystone tenant-create --name %s --description "VLAN testing"' %
                    tenant)

            msg = 'Give the admin user the role of admin in the test tenant'
            runCheck(msg, 'keystone user-role-add --user admin --tenant %s --role admin' %
                    tenant)

@roles('controller')
def VLAN_createNets():
    "Create Neutron networks for each VLAN"

    with prefix(credentials):

        for tag in vlans.keys():
            netName = 'vlan' + str(tag)
            msg = 'Create net ' + netName
            runCheck(msg, 'neutron net-create %s ' % netName + \
                    '--router:external True '
                    # '--provider:physical_network external '
                    # '--provider:network_type vlan',
                    # '--provider:network_type gre',
                    )

@roles('controller')
def VLAN_createSubnets():
    "Create Neutron subnets for each VLAN"

    with prefix(credentials):

        for tag in vlans.keys():
            netName = 'vlan' + str(tag)
            subnetName = 'vlansub' + str(tag)
            cidr = vlans[tag]
            msg = 'Create subnet ' + subnetName
            runCheck(msg, 'neutron subnet-create %s --name %s %s' % 
                    (netName, subnetName, cidr))

@roles('controller')
def VLAN_createTestInstances():
    # Assumes cirros-test has been created

    instancesPerVLAN = 1
    with prefix(credentials):

        # save net-list locally
        run('neutron net-list >net-list')

        for tag in vlans.keys():
            for number in range(instancesPerVLAN):
                instName = 'testvlan-%d-%d' % (tag, number)

                # get nic id
                netid = run("cat net-list | awk '/vlan%d/ {print $2}'" % tag, quiet=True)

                timestamp = run('date +"%Y-%m-%d %H:%M:%S"',quiet=True)
                msg = 'Create instance ' + instName
                runCheck(msg, 'nova boot --flavor m1.tiny --image cirros-test '
                        '--security-group default --nic net-id=%s %s' % (netid, instName))
                time.sleep(20)
                checkLog(timestamp)

        run('rm net-list')

@roles('controller')
def createVLANs():

    execute(VLAN_createTenant)
    execute(VLAN_createNets)
    execute(VLAN_createSubnets)
    execute(VLAN_createTestInstances)

#################################### Deployment ######################################


def deploy():
    execute(setUpVxLAN)
    execute(createVLANs)

#################################### Undeployment ######################################

@roles('compute', 'network')
def deleteBridges():
    for br in ['br-uplink','br-vlan']:
        msg = 'Delete bridge ' + br
        runCheck(msg, 'ovs-vsctl del-br ' + br)

@roles('network', 'controller')
def restoreBackups(confs):

    # The function accepts a string or a list of strings
    if type(confs) == str:
        confs = [confs]

    for conf in confs:

        backup = conf + '.bak'

        command = "if [ -e %s ]; then " % backup
        command += "rm %s; " % conf
        command += "mv %s %s; " % (backup, conf)
        command += "else echo No backup file; "
        command += "fi"

        msg = 'Restore backup for ' + conf
        runCheck(msg, command)

@roles('controller')
def removeAllInstances():

    with prefix(credentials):

        deletionCommand = "for id in $(%s | tail -n +4 | head -n -1 | awk '{print $2}'); do " + \
                "%s $id; " + \
                "done"

        msg = 'Remove all instances'
        runCheck(msg, deletionCommand % ('nova list', 'nova delete'))
        time.sleep(10)

        msg = 'Remove all routers'
        runCheck(msg, deletionCommand % ('neutron router-list', 'neutron router-delete'))
        time.sleep(10)

        msg = 'Remove all subnets'
        runCheck(msg, deletionCommand % ('neutron subnet-list', 'neutron subnet-delete'))
        time.sleep(10)

        msg = 'Remove all nets'
        runCheck(msg, deletionCommand % ('neutron net-list', 'neutron net-delete'))
        time.sleep(10)

@roles('controller')
def undeploy():
    """
    Needs testing
    """
    execute(deleteBridges)
    execute(restoreBackups, [ml2_conf_file, l3_agent_file, dhcp_agent_file])
    execute(removeAllInstances)

####################################### TDD ##########################################

@roles('controller')
def test():
    pass

def tdd():
    pass