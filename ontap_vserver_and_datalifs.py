import requests
from requests.auth import HTTPBasicAuth

# Replace these variables with your actual management IP, username, and password
management_ip = 'IP'
username = 'admin'
password = '*****'

# Base URL for the ONTAP REST API
base_url = f'https://{management_ip}/api'

# Endpoint for the network interfaces (to get data IPs)
endpoint = '/network/ip/interfaces'

# Full URL for the API call
url = base_url + endpoint

# Make the GET request with basic authentication and SSL verification
response = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()

    print("Raw Response:")
    print(data)

    print("Vserver Names from Data IPs:")
    for record in data.get('records', []):
        interface_uuid = record.get('uuid')
        interface_name = record.get('name')

        # Make a detailed request for each network interface
        detail_url = f"{base_url}/network/ip/interfaces/{interface_uuid}"
        detail_response = requests.get(detail_url, auth=HTTPBasicAuth(username, password), verify=False)

        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            ip = detail_data.get('ip', {}).get('address')
            vserver_name = detail_data.get('svm', {}).get('name')
            if ip and vserver_name:
                print(f"IP Address: {ip}, Vserver Name: {vserver_name}")
            else:
                print(f"IP Address: {ip}, Vserver Name: Unknown")
        else:
            print(f"Failed to retrieve details for interface {interface_name}: {detail_response.status_code}")
else:
    # Print the error message
    print(f"Failed to retrieve data: {response.status_code}")
    print(response.text)