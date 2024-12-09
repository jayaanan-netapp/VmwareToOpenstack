import requests
from requests.auth import HTTPBasicAuth

# Replace these variables with your actual management IP, username, and password
management_ip = 'IP'
username = 'admin'
password = '*****'

# Base URL for the ONTAP REST API
base_url = f'https://{management_ip}/api/private/cli'

# API endpoint for creating a file clone
endpoint = '/volume/file/clone/create'

# Full URL for the API call
url = base_url + endpoint

# Data for the file clone creation
data = {
    "vserver": "astra_nfs_vserver",
    "source-path": "/vol/astra_nfs/Ubuntu_vm_sai/Ubuntu_vm_sai.vmdk",
    "destination-path": "/vol/astra_nfs/Ubuntu_vm_sai/Ubuntu_vm_sai-clone.vmdk"
}

# Make the POST request with basic authentication and SSL verification
response = requests.post(url, json=data, auth=HTTPBasicAuth(username, password), verify=False)

# Check if the request was successful
if response.status_code == 200:
    print("File clone created successfully")
else:
    # Print the error message
    print(f"Failed to create file clone: {response.status_code}")
    print(response.text)