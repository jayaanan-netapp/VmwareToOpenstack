from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl

def get_vm_details(service_instance):
    content = service_instance.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vms = container.view
    container.Destroy()

    vm_details = []
    for vm in vms:
        summary = vm.summary
        vm_info = {
            'name': summary.config.name,
            'instance_uuid': summary.config.instanceUuid,
            'datastore': [ds.info.name for ds in vm.datastore]
        }
        vm_details.append(vm_info)
    return vm_details

def get_datastore_details(service_instance):
    content = service_instance.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    datastores = container.view
    container.Destroy()

    datastore_details = []
    for ds in datastores:
        summary = ds.summary
        ds_info = {
            'name': summary.name,
            'capacity': summary.capacity,
            'free_space': summary.freeSpace
        }
        datastore_details.append(ds_info)
    return datastore_details

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
        vm_details = get_vm_details(service_instance)
        datastore_details = get_datastore_details(service_instance)

        print("VM Details:")
        for vm in vm_details:
            print(vm)

        print("\nDatastore Details:")
        for ds in datastore_details:
            print(ds)

    finally:
        Disconnect(service_instance)

if __name__ == "__main__":
    main()