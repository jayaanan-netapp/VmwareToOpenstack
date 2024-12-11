# VmwareToOpenstack
This project is to migrate VMs from Vmware to Openstack using ONTAP technologies to optimized migration. The project is divided into 3 steps:
1. Get VMs from Vmware to clone VMDK file in ONTAP. Takes less than second.
2. Convert VMDK to QCOW2 format. Compute intensive. This can be optimized by placing converter file in ONTAP file system.
3. Upload QCOW2 file to Openstack using Cinder boot volume.