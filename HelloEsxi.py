hostname = 'esxi-29-210.nb.openenglab.netapp.com'
username = 'root'
password = 'Netapp@123'

from pyVim.connect import SmartConnect
from vmware.vapi.vsphere.client import create_vsphere_client, VsphereClient
import requests, urllib3
import sys
from pyVmomi import vim

def connect(host: str, user: str, pwd: str, insecure: bool) -> tuple[VsphereClient, vim.ServiceInstance]:
    session = requests.session()
    if insecure:
        session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print('Creating an Automation API session.')
    vsphere_client = create_vsphere_client(host, user, pwd, session=session)
    print('Creating a VIM/SOAP session.')
    si = SmartConnect(host=host,
                      user=user,
                      pwd=pwd,
                      disableSslCertValidation=insecure)
    return vsphere_client, si

(vsphere_client, service_instance) = connect(hostname,
                                             username,
                                             password,
                                             insecure=True)