import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import requests
from requests.auth import HTTPBasicAuth
import socket
import time

app = Flask(__name__)
CORS(app)

management_ip = 'IP'
username = 'admin'
password = '*****'

base_url = f'https://{management_ip}/api'
endpoint = '/network/ip/interfaces'
url = base_url + endpoint

def resolve_hostname(hostname):
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        print(f"Failed to resolve hostname: {hostname}")
        return None

def get_vserver_name_from_data_ip(data_ip):
    resolved_ip = resolve_hostname(data_ip) if not data_ip.replace('.', '').isdigit() else data_ip
    if not resolved_ip:
        return None
    response = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False)
    if response.status_code == 200:
        data = response.json()
        for record in data.get('records', []):
            interface_uuid = record.get('uuid')
            detail_url = f"{base_url}/network/ip/interfaces/{interface_uuid}"
            detail_response = requests.get(detail_url, auth=HTTPBasicAuth(username, password), verify=False)
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                ip = detail_data.get('ip', {}).get('address')
                vserver_name = detail_data.get('svm', {}).get('name')
                if ip == resolved_ip:
                    return vserver_name
            else:
                print(f"Failed to retrieve details for interface {interface_uuid}: {detail_response.status_code}")
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        print(response.text)
    return None

def get_volume_details(vserver_name, volume_name):
    volume_endpoint = f"/storage/volumes?svm.name={vserver_name}&name={volume_name}"
    volume_url = base_url + volume_endpoint
    response = requests.get(volume_url, auth=HTTPBasicAuth(username, password), verify=False)
    if response.status_code == 200:
        data = response.json()
        if data.get('records'):
            volume_details = data['records'][0]
            return volume_details
        else:
            print(f"No volume found with name {volume_name} in vserver {vserver_name}")
    else:
        print(f"Failed to retrieve volume details: {response.status_code}")
        print(response.text)
    return None

def create_file_clone(vserver_name, volume_name, volume_uuid, source_path, destination_path):
    clone_endpoint = "/storage/file/clone"
    clone_url = base_url + clone_endpoint
    clone_body = {
        "volume": {
            "name": volume_name,
            "uuid": volume_uuid
        },
        "source_path": source_path,
        "destination_path": destination_path
    }
    response = requests.post(clone_url, auth=HTTPBasicAuth(username, password), json=clone_body, verify=False)
    if response.status_code == 202:
        data = response.json()
        job_uuid = data.get('job', {}).get('uuid')
        print(f"Clone creation job started with UUID: {job_uuid}")
        return job_uuid
    else:
        print(f"Failed to create file clone: {response.status_code}")
        print(response.text)
    return None

def poll_job_status(job_uuid, timeout=60, interval=5):
    job_url = f"{base_url}/cluster/jobs/{job_uuid}"
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(job_url, auth=HTTPBasicAuth(username, password), verify=False)
        if response.status_code == 200:
            job_data = response.json()
            job_status = job_data.get('state')
            if job_status in ['success', 'failure']:
                print(f"Job {job_uuid} completed with status: {job_status}")
                if job_status == 'failure':
                    failure_reason = job_data.get('message', 'No failure reason provided')
                    print(f"Failure reason: {failure_reason}")
                return job_status
            else:
                print(f"Job {job_uuid} is still in progress...")
        else:
            print(f"Failed to retrieve job status: {response.status_code}")
            print(response.text)
        time.sleep(interval)
    print(f"Job {job_uuid} did not complete within the timeout period")
    return None

def clone_vmware_vmdk(data_ip, source_path, destination_path):
    vserver_name = get_vserver_name_from_data_ip(data_ip)
    if vserver_name:
        print(f"Vserver Name for IP {data_ip}: {vserver_name}")
        volume_name = 'astra_nfs'
        volume_details = get_volume_details(vserver_name, volume_name)
        if volume_details:
            print(f"Volume Details for {volume_name} in vserver {vserver_name}:")
            print(volume_details)
            job_uuid = create_file_clone(vserver_name, volume_name, volume_details['uuid'], source_path, destination_path)
            if job_uuid:
                poll_job_status(job_uuid, timeout=60, interval=5)
    else:
        print(f"Vserver Name for IP {data_ip} not found")

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
            destination_vmdk_path = None
            for datastore in vm_info['datastores']:
                if not remote_host:
                    remote_host = datastore['remote_host']
            for file in vm_info['files']:
                if file['path'].endswith('.vmdk'):
                    first_vmdk_path = file['path'].split('] ')[1]
                    destination_vmdk_path = first_vmdk_path.replace('.vmdk', '_clone.vmdk')
                    break

            print(f"Remote Host: {remote_host}")
            print(f"First VMDK Path: {first_vmdk_path}")
            clone_vmware_vmdk(remote_host, first_vmdk_path, destination_vmdk_path)
            return jsonify(vm_info)
        else:
            return jsonify({"error": "VM not found"}), 404
    finally:
        Disconnect(service_instance)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)