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
        #print(f"Checking datastore: {ds.summary.name}")  # Debugging line
        #print(f"Datastore info type: {type(ds.info)}")  # Debugging line
        if isinstance(ds.info, vim.host.NasDatastoreInfo):
            #print(f"Found NFS datastore: {ds.summary.name}")  # Debugging line
            # Print all attributes of the ds.info object
            #print(f"Attributes of ds.info: {dir(ds.info)}")  # Debugging line
            nfs_info = {
                'name': ds.info.name,
                'remote_host': ds.info.nas.remoteHost,  # Accessing remoteHost from nas attribute
                'remote_path': ds.info.nas.remotePath,  # Accessing remotePath from nas attribute
                'capacity': ds.summary.capacity,
                'free_space': ds.summary.freeSpace,
                'accessible': ds.summary.accessible
            }
            nfs_datastores.append(nfs_info)
    return nfs_datastores

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

        print("NFS Datastores:")
        for nfs in nfs_datastores:
            print(f"Name: {nfs['name']}")
            print(f"Remote Host: {nfs['remote_host']}")
            print(f"Remote Path: {nfs['remote_path']}")
            print(f"Capacity: {nfs['capacity']}")
            print(f"Free Space: {nfs['free_space']}")
            print(f"Accessible: {nfs['accessible']}")
            print()

    finally:
        Disconnect(service_instance)

if __name__ == "__main__":
    main()