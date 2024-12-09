from netapp_ontap import config, HostConnection
from netapp_ontap.resources import IpInterface

# Replace these variables with your actual management IP, username, and password
management_ip = 'IP'
username = 'admin'
password = '*****'

# Configure the connection to the ONTAP cluster
config.CONNECTION = HostConnection(
    host=management_ip,
    username=username,
    password=password,
    verify=False  # Set to True and provide a path to a CA bundle in production
)

# Function to get and print all data IPs
def get_data_ips():
    try:
        # Retrieve all IP interfaces
        ip_interfaces = IpInterface.get_collection()

        print("Data IPs:")
        for ip_interface in ip_interfaces:
            # Fetch the details of each IP interface
            ip_interface.get()
            if ip_interface.ip:
                print(ip_interface.ip.address)
    except Exception as e:
        print(f"Failed to retrieve data IPs: {e}")

# Call the function to get and print data IPs
get_data_ips()