import requests
from requests.auth import HTTPBasicAuth
import socket
import time

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

if __name__ == "__main__":
    data_ip = 'data_ip or hostname'
    source_path = 'ostack-centos-01/ostack-centos-01.vmdk'
    destination_path = 'ostack-centos-01/ostack-centos-01_clone.vmdk'
    clone_vmware_vmdk(data_ip, source_path, destination_path)