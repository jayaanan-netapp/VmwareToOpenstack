from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import time

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
            'ip_address': guest.ipAddress if guest else 'N/A',
            'files': []
        }

        for ds in vm.datastore:
            for nfs_ds in datastores:
                if ds.info.name == nfs_ds['name']:
                    vm_info['files'] = get_vm_files(ds, vm)
                    nfs_ds['vms'].append(vm_info)

def get_vm_files(datastore, vm):
    files = []
    browser = datastore.browser
    search_spec = vim.host.DatastoreBrowser.SearchSpec()
    search_spec.matchPattern = ["*.vmdk", "*.vmx", "*.log"]
    vm_folder_path = f"[{datastore.info.name}] {vm.summary.config.name}/"
    search_task = browser.SearchDatastore_Task(vm_folder_path, search_spec)

    while search_task.info.state == vim.TaskInfo.State.running:
        time.sleep(1)

    if search_task.info.state == vim.TaskInfo.State.success:
        search_task_result = search_task.info.result
        if search_task_result:
            for result in search_task_result.file:
                file_info = {
                    'path': vm_folder_path + result.path,
                    'size': result.fileSize,
                    'type': type(result).__name__
                }
                files.append(file_info)
        else:
            print(f"No files found in datastore: {datastore.info.name}")
    else:
        print(f"Search task failed for datastore: {datastore.info.name}")
        print(f"Error: {search_task.info.error}")
        print(f"Error type: {type(search_task.info.error)}")

    return files

def main():
    context = ssl._create_unverified_context()

    service_instance = SmartConnect(
        host='esxi-ip',
        user='root',
        pwd='esxi_pass',
        sslContext=context
    )

    try:
        nfs_datastores = get_nfs_datastores(service_instance)
        get_vm_details(service_instance, nfs_datastores)

        print("NFS Datastores and Attached VMs:")
        for nfs in nfs_datastores:
            print(f"Datastore Name: {nfs['name']}")
            print(f"Remote Host: {nfs['remote_host']}")
            print(f"Remote Path: {nfs['remote_path']}")
            print(f"Capacity: {nfs['capacity']}")
            print(f"Free Space: {nfs['free_space']}")
            print(f"Accessible: {nfs['accessible']}")
            print("Attached VMs:")
            for vm in nfs['vms']:
                print(f"  VM Name: {vm['name']}")
                print(f"  CPU: {vm['cpu']} vCPUs")
                print(f"  Memory: {vm['memory']} MB")
                print(f"  Power State: {vm['power_state']}")
                print(f"  IP Address: {vm['ip_address']}")
                print("  Files:")
                for file in vm['files']:
                    print(f"    Path: {file['path']}")
                    print(f"    Size: {file['size']} bytes")
                    print(f"    Type: {file['type']}")
                print()
            print()

    finally:
        Disconnect(service_instance)

if __name__ == "__main__":
    main()