import sys
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

def get_vm_details(service_instance, datastores, vm_name):
    content = service_instance.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vms = container.view
    container.Destroy()

    for vm in vms:
        summary = vm.summary
        config = summary.config
        runtime = summary.runtime
        guest = summary.guest

        if config.name == vm_name:
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
            return vm_info
    return None

def get_vm_files(datastore, vm):
    files = []
    browser = datastore.browser
    search_spec = vim.host.DatastoreBrowser.SearchSpec()
    search_spec.matchPattern = ["*.vmdk", "*.vmx", "*.log"]  # Example patterns to search for specific file types
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

def print_vm_details(vm_info):
    if vm_info:
        print(f"VM Name: {vm_info['name']}")
        print(f"  CPU: {vm_info['cpu']} vCPUs")
        print(f"  Memory: {vm_info['memory']} MB")
        print(f"  Power State: {vm_info['power_state']}")
        print(f"  IP Address: {vm_info['ip_address']}")
        print("  Files:")
        for file in vm_info['files']:
            print(f"    Path: {file['path']}")
            print(f"    Size: {file['size']} bytes")
            print(f"    Type: {file['type']}")
        print()
    else:
        print("VM not found")

def main():
    '''if len(sys.argv) != 2:
        print("Usage: python script.py <vm_name>")
        sys.exit(1)

    vm_name = sys.argv[1]'''
    vm_name = "ostack-centos-01"

    context = ssl._create_unverified_context()

    service_instance = SmartConnect(
        host='esxi-ip',
        user='root',
        pwd='esxi_pass',
        sslContext=context
    )

    try:
        nfs_datastores = get_nfs_datastores(service_instance)
        vm_info = get_vm_details(service_instance, nfs_datastores, vm_name)
        print_vm_details(vm_info)

    finally:
        Disconnect(service_instance)

if __name__ == "__main__":
    main()