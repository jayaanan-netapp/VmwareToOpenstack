import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import time

app = Flask(__name__)
CORS(app)

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
                'files': [],
                'datastores': []
            }

            for ds in vm.datastore:
                for nfs_ds in datastores:
                    if ds.info.name == nfs_ds['name']:
                        vm_info['files'] = get_vm_files(ds, vm)
                        datastore_info = {
                            'name': nfs_ds['name'],
                            'remote_host': nfs_ds['remote_host'],
                            'remote_path': nfs_ds['remote_path'],
                            'capacity': nfs_ds['capacity'],
                            'free_space': nfs_ds['free_space'],
                            'accessible': nfs_ds['accessible']
                        }
                        vm_info['datastores'].append(datastore_info)
                        nfs_ds['vms'].append(vm_info)

            return vm_info
    return None

def get_vm_files(datastore, vm):
    files = []
    browser = datastore.browser
    search_spec = vim.host.DatastoreBrowser.SearchSpec()
    search_spec.matchPattern = ["*.vmdk"]
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

@app.route('/vm-details', methods=['GET'])
def vm_details():
    vm_name = request.args.get('vm_name')
    if not vm_name:
        return jsonify({"error": "vm_name parameter is required"}), 400

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
        if vm_info:
            remote_host = None
            first_vmdk_path = None
            for datastore in vm_info['datastores']:
                if not remote_host:
                    remote_host = datastore['remote_host']
            for file in vm_info['files']:
                if file['path'].endswith('.vmdk'):
                    first_vmdk_path = file['path'].split('] ')[1]
                    break

            print(f"Remote Host: {remote_host}")
            print(f"First VMDK Path: {first_vmdk_path}")

            return jsonify(vm_info)
        else:
            return jsonify({"error": "VM not found"}), 404
    finally:
        Disconnect(service_instance)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)