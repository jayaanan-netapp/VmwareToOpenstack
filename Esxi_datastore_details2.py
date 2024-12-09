from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl

def get_nfs_datastores(service_instance):
    content = service_instance.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    datastores = container.view
    container.Destroy()

    nfs_datastores = []
    for ds in datastores:
        if isinstance(ds.info, vim.host.NasDatastoreInfo):
            nfs_info = {
                'name': ds.info.name,
                'remote_host': ds.info.nas.remoteHost,
                'remote_path': ds.info.nas.remotePath,
                'capacity': ds.summary.capacity,
                'free_space': ds.summary.freeSpace,
                'accessible': ds.summary.accessible,
                'vms': []
            }
            nfs_datastores.append(nfs_info)
    return nfs_datastores

def get_vm_details(service_instance, datastores):
    content = service_instance.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vms = container.view
    container.Destroy()

    for vm in vms:
        summary = vm.summary
        config = summary.config
        runtime = summary.runtime
        guest = summary.guest

        vm_info = {
            'name': config.name,
            'cpu': config.numCpu,
            'memory': config.memorySizeMB,
            'power_state': runtime.powerState,
            'ip_address': guest.ipAddress if guest else 'N/A'
        }

        for ds in vm.datastore:
            for nfs_ds in datastores:
                if ds.info.name == nfs_ds['name']:
                    nfs_ds['vms'].append(vm_info)

def main():
    # Disable SSL certificate verification
    context = ssl._create_unverified_context()

    # Connect to the vSphere server
    service_instance = SmartConnect(
        host='esxi-ip',
        user='root',
        pwd='esxi_pass',
        sslContext=context
    )

    try:
        nfs_datastores = get_nfs_datastores(service_instance)
        get_vm_details(service_instance, nfs_datastores)

        #print("VMs and attached datastore:")
        for nfs in nfs_datastores:
            '''print(f"Datastore Name: {nfs['name']}")
            print(f"Remote Host: {nfs['remote_host']}")
            print(f"Remote Path: {nfs['remote_path']}")
            print(f"Capacity: {nfs['capacity']}")
            print(f"Free Space: {nfs['free_space']}")
            print(f"Accessible: {nfs['accessible']}")
            print("Attached VMs:")'''
            for vm in nfs['vms']:
                print(f"VM Name: {vm['name']}")
                print(f"CPU: {vm['cpu']} vCPUs")
                print(f"Memory: {vm['memory']} MB")
                print(f"Power State: {vm['power_state']}")
                print(f"IP Address: {vm['ip_address']}")
                print("====== data store detaols=====")
                print(f"    Datastore Name: {nfs['name']}")
                print(f"    Remote Host: {nfs['remote_host']}")
                print(f"    Remote Path: {nfs['remote_path']}")
                print(f"    Capacity: {nfs['capacity']}")
                print(f"    Free Space: {nfs['free_space']}")
                print(f"    Accessible: {nfs['accessible']}")
                print("     Attached VMs:")
            print()

    finally:
        Disconnect(service_instance)

if __name__ == "__main__":
    main()