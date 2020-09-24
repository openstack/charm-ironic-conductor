# Overview

This charm provides the Ironic bare metal conductor service for an OpenStack cloud, starting with train. To get a fully functional Ironic deployment, you will also need the ```ironic-api``` and ```neutron-api-plugin-ironic``` charms to be deployed.

# Deployment

To deploy (partial deployment only):

```bash
juju deploy nova-compute \
  --config virt-type="ironic" nova-ironic
juju deploy ironic-conductor

juju add-relation nova-ironic ironic-api
juju add-relation ironic-conductor ironic-api
juju add-relation ironic-conductor keystone
juju add-relation ironic-conductor rabbitmq-server
juju add-relation ironic-conductor mysql
```

# Configuration

There are a number of configuration parameters that greatly influence how the Ironic conductor service will behave. We will detail the ones that require special consideration.

## Deployment interfaces

The Ironic conductor charm currently supports two deployment interfaces:

  * direct
  * iscsi

### The iSCSI deployment interface

How it works (really high level view):

  * Ironic python agent boots on remote bare metal machine
  * Ironic python agent exports all disks as iSCSI targets
  * Ironic conductor logs into the iSCSI target and writes the operating system image to the target disk

Pros:

  * Minimal requirements in terms of supporting services (glance, swift, etc)

Cons:

  * The **ironic-conductor** service needs to be deployed on a bare metal server, or inside a VM. Containerizing the conductor service will make the iscsi deployment method, fail.
  The reason for this is that the iscsi kernel module is not namespaced at all, and any attempt to log into an iSCSI target, will happen on the host, not inside the container.
  * Heavy lifting is done by conductor itself:
    * Downloading and converting the Glance image
    * Writing the disk data to the iSCSI target
    * Applying any post-write configuration
  * Requires more Ironic conductor units as the number of bare metal nodes increases

You can set this deployment interface by running the following commands:

```bash
juju config ironic-conductor \
  enabled-deploy-interfaces="iscsi, direct"
  default-deploy-interface="iscsi"
```

The default deploy interface can be overwritten for individual bare metal nodes setting the **--deploy-interface** explicitly:

```bash
openstack baremetal node set $NODE_NAME --deploy-interface iscsi
```

Whenever possible, avoid using the iSCSI deployment interface, in favor of the **direct** deployment interface.

### The direct deployment interface

How it works (really high level view):

  * The Ironic python agent boots on a remote bare metal machine
  * The Ironic agent fetches any needed images from glance and writes them to local storage.

Pros:

  * All heavy lifting is done by the node that is getting deployed
  * The Ironic conductor can be deployed inside an LXD container
  * Fewer Ironic conductor units are needed, as no real processing is done on these machines

Cons:

  * Requires the whole Operating system image to fit in the node’s memory, except when using raw images. Raw images are streamed directly to disk.

Special considerations:

  * Glance must be related to Swift/RadosGW, and support multi-backend, or use **object-store** as its default storage backend
  * Ironic relies on being able to generate [temporary URLs](https://docs.openstack.org/swift/latest/api/temporary_url_middleware.html)
    * The **set-temp-url-secret** action must be run to properly set **Temp-Url-Key**
  * If **ceph-radosgw** is used, it _must_ be deployed with the **namespace-tenants** options set to _**true**_

You can set this deployment interface by running the following commands:

```bash
juju config ironic-conductor \
  enabled-deploy-interfaces="iscsi, direct"
  default-deploy-interface="direct"
```

The default deploy interface can be overwritten for individual bare metal nodes setting the **--deploy-interface** explicitly:

```bash
openstack baremetal node set $NODE_NAME --deploy-interface direct
```

## Network interfaces

Ironic can be configured for multi-tenancy by leveraging the **neutron** network interface.

The currently supported network interfaces are:
  * neutron
  * flat
  * noop

When using the **neutron** network interface, the following configuration options become mandatory:

  * provisioning-network
  * cleaning-network

These networks will need to be created by the operator beforehand.

For details and security considerations in regards to the selected network interfaces, please refer to the [Configure tenant networks](https://docs.openstack.org/ironic/latest/install/configure-tenant-networks.html) section of the Ironic documentation.

Pay close attention to the notes and security warnings highlighted on that page.

## Neutron configuration

If using the **flat** network interface, the following configurations will need to be made on ```neutron-gateway```:

```bash
juju config neutron-gateway \
	enable-isolated-metadata=true \
	enable-metadata-network=true
```

This will allow ironic nodes to access their metadata. Routes will be pushed to them via DHCP that will allow access to ```169.254.169.254```.

## Misc options

The following options may also be of interest:

  * pxe-append-params - You may use this to pass any additional options to the linux kernel, or the Ironic Python Agent (IPA) during deployment. For a list of IPA flags that can be set (ipa-insecure, ssh public key, root password, etc), please see the [IPA documentation page](https://docs.openstack.org/ironic-python-agent/latest/index.html)
  * automated-cleaning - enables (default) or disables automated cleaning of nodes.
  * disable-secure-erase - disables secure erase of bare metal instance disks, on release. By default, secure erase is enabled. Set this option to **true** to disable secure erase. Useful for testing.

Please refer to the charm config for a complete list of available charm options. 
