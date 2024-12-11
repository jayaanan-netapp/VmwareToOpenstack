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
import subprocess
import os
import re

app = Flask(__name__)
CORS(app)

management_ip = 'ip'
username = 'admin'
password = 'pass'

base_url = f'https://{management_ip}/api'
endpoint = '/network/ip/interfaces'
url = base_url + endpoint

# Can be updated to OpenStack REST API in future
def set_environment_variables():
    env_vars = dict(os.environ)
    env_vars["OS_PROJECT_DOMAIN_ID"] = "default"
    env_vars["OS_USER_DOMAIN_ID"] = "default"
    env_vars["OS_AUTH_URL"] = "http://ip/identity"
    env_vars["OS_PROJECT_NAME"] = "admin"
    env_vars["OS_USERNAME"] = "admin"
    env_vars["OS_PASSWORD"] = "pass"
    return env_vars


def run_command(command, env_vars=None):
    result = subprocess.run(command, shell=True, env=env_vars, executable="/bin/bash", capture_output=True, text=True)
    return result.stdout.strip()


def convert_image(full_path, source_image, destination_image, env_vars):
    command = "cd " + full_path + "; qemu-img convert -f vmdk -O qcow2 " + source_image + " " + destination_image
    print(command)
    return run_command(command, env_vars)

def get_pool_name(ip, env_vars):
    pool_command = f"cinder get-pools | grep {ip} | awk '{{print $4}}'"
    return run_command(pool_command, env_vars)


def get_source_path_from_nfs_shares(nfs_shares, env_vars):
    source_path_cmd = "mount | grep -f "+ nfs_shares + " | awk '{print $3}'"
    return run_command(source_path_cmd, env_vars)

def get_source_backend_name(ip, nfs_shares, env_vars):
    source_backend_command = f"cat " + nfs_shares +" | grep "+ ip +" | awk '{{print $1}}'"
    return run_command(source_backend_command, env_vars)

def manage_volume(pool_name, actual_file, volume_name, env_vars):
    manage_command = f"cinder manage --id-type source-name {pool_name} {actual_file} --name {volume_name} --bootable"
    manage_output = run_command(manage_command, env_vars)
    id_match = re.search(r"\| id\s+\|\s+([\w-]+)\s+\|", manage_output)
    if id_match:
        volume_id = id_match.group(1)
        print(volume_id)
    else:
        print("Volume ID not found in the output.")
    return volume_id

def resize_volume(full_path, destination_image, volume_id, env_vars):
    virtual_size_command = "cd " + full_path + "; qemu-img info " + destination_image + " | grep virtual | awk '{print $3}'"
    virtual_size = run_command(virtual_size_command, env_vars)
    cinder_resize_command = "openstack volume set --size " + virtual_size + " " + volume_id
    return run_command(cinder_resize_command, env_vars)

def create_vm(vm_name, volume_id, env_vars):
    vm_create_command = "nova boot --flavor d4 --boot-volume " + volume_id + " --nic net-id=0e08ba5f-1c5b-4069-a8b9-e86f7c34a736 " + vm_name
    vm_create_output = run_command(vm_create_command, env_vars)
    vm_id = ""
    id_match = re.search(r"\| id\s+\|\s+([\w-]+)\s+\|", vm_create_output)
    if id_match:
        vm_id = id_match.group(1)
    else:
        print("VM ID not found in the output.")
    time.sleep(15)
    return vm_id

def create_floating_ip(floating_ip_address, public_network_id, env_vars):
    ip_create_command = "openstack floating ip create " + public_network_id + " --floating-ip-address " + floating_ip_address
    return run_command(ip_create_command, env_vars)

def assign_floating_ip_to_vm(vm_id, floating_ip_address, env_vars):
    ip_assign_command = "openstack server add floating ip " + vm_id + " " + floating_ip_address
    return run_command(ip_assign_command, env_vars)

def migrate_to_open_stack(source_image, ip, vm_name):
    env_vars = set_environment_variables()
    print(env_vars)

    subprocess.run(["ls", "-l"])
    subprocess.run(['cinder list'], shell=True, env=env_vars, executable="/bin/bash")
    #vm_name = "Ubuntu_vm_sai"
    #vm_name = vm_name
    volume_name = "hack_new_vol1"
    floating_ip_address = "ip"
    public_network_id = "fae6935c-0bbf-49f3-86a9-be20a26220be"

    destination_image = source_image.replace(".vmdk", ".qcow2")
    nfs_shares = "/etc/cinder/nfs_shares1"
    source_path = get_source_path_from_nfs_shares(nfs_shares, env_vars)

    convert_image(source_path, source_image, destination_image, env_vars)

    pool_name = get_pool_name(ip, env_vars)
    print(pool_name)

    source_backend_name = get_source_backend_name(ip, nfs_shares, env_vars)
    print(source_backend_name)

    actual_file = f"{source_backend_name}/{destination_image}"
    print(actual_file)

    volume_id = manage_volume(pool_name, actual_file, volume_name, env_vars)

    resize_volume(source_path, destination_image, volume_id, env_vars)

    vm_id = create_vm(vm_name, volume_id, env_vars)

    create_floating_ip(floating_ip_address, public_network_id, env_vars)

    assign_floating_ip_to_vm(vm_id, floating_ip_address, env_vars)


def resolve_hostname(hostname):
    try:
        remote_ip = socket.gethostbyname(hostname)
        print(f"Remote IP: {remote_ip}")
        return remote_ip
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
            job_uuid = create_file_clone(vserver_name, volume_name, volume_details['uuid'], source_path,
                                         destination_path)
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
        host='esxi_ip',
        user='root',
        pwd='pass',
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
            remote_ip = resolve_hostname(remote_host) if not remote_host.replace('.', '').isdigit() else remote_host
            vm_name = vm_info['name']
            print(f"VM name: {vm_name}")
            print(f"Remote Host: {remote_host}")
            print(f"Remote IP: {remote_ip}")
            print(f"First VMDK Path: {first_vmdk_path}")
            print(f"Destination VMDK Path: {destination_vmdk_path}")
            clone_vmware_vmdk(remote_host, first_vmdk_path, destination_vmdk_path)
            migrate_to_open_stack(destination_vmdk_path, remote_ip, vm_name)
            return jsonify(vm_info)
        else:
            return jsonify({"error": "VM not found"}), 404
    finally:
        Disconnect(service_instance)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
