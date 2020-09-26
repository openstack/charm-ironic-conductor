from __future__ import absolute_import

import collections
import os

import charms_openstack.charm
import charms_openstack.adapters
from charms_openstack.adapters import (
    RabbitMQRelationAdapter,
    DatabaseRelationAdapter,
    OpenStackRelationAdapters,
)
from charmhelpers.contrib.openstack.utils import os_release

import charm.openstack.ironic.controller_utils as controller_utils
import charms_openstack.adapters as adapters
import charmhelpers.contrib.network.ip as ch_ip
import charms.leadership as leadership
import charms.reactive as reactive

PACKAGES = [
    'ironic-conductor',
    'python3-dracclient',
    'python3-keystoneauth1',
    'python3-keystoneclient',
    'python3-glanceclient',
    'python3-sushy',
    'python3-swiftclient',
    'python3-mysqldb',
    'python3-ironicclient',
    'shellinabox',
    'openssl',
    'socat',
    'open-iscsi',
    'qemu-utils',
    'ipmitool']

IRONIC_DIR = "/etc/ironic/"
IRONIC_CONF = os.path.join(IRONIC_DIR, "ironic.conf")
ROOTWRAP_CONF = os.path.join(IRONIC_DIR, "rootwrap.conf")
FILTERS_DIR = os.path.join(IRONIC_DIR, "rootwrap.d")
IRONIC_LIB_FILTERS = os.path.join(
    FILTERS_DIR, "ironic-lib.filters")
IRONIC_UTILS_FILTERS = os.path.join(
    FILTERS_DIR, "ironic-utils.filters")
TFTP_CONF = "/etc/default/tftpd-hpa"
HTTP_SERVER_CONF = "/etc/nginx/nginx.conf"
VALID_NETWORK_INTERFACES = ["neutron", "flat", "noop"]
VALID_DEPLOY_INTERFACES = ["direct", "iscsi"]
DEFAULT_DEPLOY_IFACE = "flat"
DEFAULT_NET_IFACE = "direct"

# The IPMI HW type requires only ipmitool to function. This HW type
# remains pretty much unchanged across OpenStack releases and *should*
# work
_NOOP_INTERFACES = {
    'enabled_bios_interfaces': 'no-bios',
    'enabled_management_interfaces': 'noop',
    'enabled_inspect_interfaces': 'no-inspect',
    'enabled_console_interfaces': 'no-console',
    'enabled_raid_interfaces': 'no-raid',
    'enabled_vendor_interfaces': 'no-vendor',
}
_IPMI_HARDWARE_TYPE = {
    'needed_packages': ['ipmitool', 'shellinabox', 'socat'],
    'config_options': {
        'enabled_hardware_types': ['ipmi', 'intel-ipmi'],
        'enabled_management_interfaces': [
            'ipmitool', 'intel-ipmitool'],
        'enabled_inspect_interfaces': [],
        'enabled_power_interfaces': ['ipmitool'],
        'enabled_console_interfaces': [
            'ipmitool-socat',
            'ipmitool-shellinabox'],
        'enabled_raid_interfaces': [],
        'enabled_vendor_interfaces': ['ipmitool'],
        'enabled_boot_interfaces': ['pxe'],
        'enabled_bios_interfaces': []
    }
}

_HW_TYPES_MAP = collections.OrderedDict([
    ('train', {
        'ipmi': _IPMI_HARDWARE_TYPE,
        'redfish': {
            'needed_packages': ['python3-sushy'],
            'config_options': {
                'enabled_hardware_types': ['redfish'],
                'enabled_management_interfaces': ['redfish'],
                'enabled_inspect_interfaces': ['redfish'],
                'enabled_power_interfaces': ['redfish'],
                'enabled_console_interfaces': [],
                'enabled_raid_interfaces': [],
                'enabled_vendor_interfaces': [],
                'enabled_boot_interfaces': ['pxe'],
                'enabled_bios_interfaces': []
            }
        },
        'idrac': {
            'needed_packages': ['python-dracclient', 'python3-sushy'],
            'config_options': {
                'enabled_hardware_types': ['idrac'],
                'enabled_management_interfaces': ['idrac-redfish'],
                'enabled_inspect_interfaces': ['idrac-redfish'],
                'enabled_power_interfaces': ['idrac-redfish'],
                'enabled_console_interfaces': [],
                'enabled_raid_interfaces': ['idrac-wsman'],
                'enabled_vendor_interfaces': ['idrac-wsman'],
                'enabled_boot_interfaces': ['pxe'],
                'enabled_bios_interfaces': []
            }
        }
    }),
    ('ussuri', {
        'ipmi': _IPMI_HARDWARE_TYPE,
        'redfish': {
            'needed_packages': ['python3-sushy'],
            'config_options': {
                'enabled_hardware_types': ['redfish'],
                'enabled_management_interfaces': ['redfish'],
                'enabled_inspect_interfaces': ['redfish'],
                'enabled_power_interfaces': ['redfish'],
                'enabled_console_interfaces': [],
                'enabled_raid_interfaces': [],
                'enabled_vendor_interfaces': [],
                'enabled_boot_interfaces': ['pxe', 'redfish-virtual-media'],
                'enabled_bios_interfaces': [],
            }
        },
        'idrac': {
            'needed_packages': ['python-dracclient', 'python3-sushy'],
            'config_options': {
                'enabled_hardware_types': ['idrac'],
                'enabled_management_interfaces': ['idrac-redfish'],
                'enabled_inspect_interfaces': ['idrac-redfish'],
                'enabled_power_interfaces': ['idrac-redfish'],
                'enabled_console_interfaces': [],
                'enabled_raid_interfaces': ['idrac-wsman'],
                'enabled_vendor_interfaces': ['idrac-wsman'],
                'enabled_boot_interfaces': ['pxe'],
                'enabled_bios_interfaces': ['idrac-wsman']
            }
        }
    })
])

OPENSTACK_RELEASE_KEY = 'ironic-charm.openstack-release-version'


# select the default release function
charms_openstack.charm.use_defaults('charm.default-select-release')


@adapters.config_property
def deployment_interface_ip(args):
    return ch_ip.get_relation_ip("deployment")


@adapters.config_property
def internal_interface_ip(args):
    return ch_ip.get_relation_ip("internal")


@adapters.config_property
def temp_url_secret(args):
    url_secret = leadership.leader_get("temp_url_secret")
    return url_secret


class IronicAdapters(OpenStackRelationAdapters):

    relation_adapters = {
        'amqp': RabbitMQRelationAdapter,
        'shared_db': DatabaseRelationAdapter,
    }


class IronicConductorCharm(charms_openstack.charm.OpenStackCharm):

    adapters_class = IronicAdapters

    abstract_class = False
    release = 'train'
    name = 'ironic'
    packages = PACKAGES
    python_version = 3

    service_type = 'ironic'
    default_service = 'ironic-conductor'
    services = ['ironic-conductor', 'tftpd-hpa']

    required_relations = [
        'shared-db', 'amqp', 'identity-credentials', 'ironic-api']

    restart_map = {
        IRONIC_CONF: ['ironic-conductor', ],
        IRONIC_UTILS_FILTERS: ['ironic-conductor', ],
        IRONIC_LIB_FILTERS: ['ironic-conductor', ],
        ROOTWRAP_CONF: ['ironic-conductor', ],
    }

    # Package for release version detection
    release_pkg = 'ironic-common'

    # Package codename map for ironic-common
    package_codenames = {
        'ironic-common': collections.OrderedDict([
            ('13', 'train'),
            ('15', 'ussuri'),
            ('16', 'victoria'),
        ]),
    }

    group = "ironic"
    mandatory_config = [
        "enabled-network-interfaces",
        "enabled-deploy-interfaces",
    ]

    def __init__(self, **kw):
        super().__init__(**kw)
        self.pxe_config = controller_utils.get_pxe_config_class(
            self.config)
        self._setup_pxe_config(self.pxe_config)
        self._setup_power_adapter_config()
        self._configure_defaults()
        if "neutron" in self.enabled_network_interfaces:
            self.mandatory_config.extend([
                "provisioning-network",
                "cleaning-network"])

    def _configure_defaults(self):
        net_iface = self.config.get("default-network-interface", None)
        if not net_iface:
            self.config["default-network-interface"] = DEFAULT_NET_IFACE
        iface = self.config.get("default-deploy-interface", None)
        if not iface:
            self.config["default-deploy-interface"] = DEFAULT_DEPLOY_IFACE

    def _get_hw_type_map(self):
        release = os_release(self.release_pkg)
        supported = list(_HW_TYPES_MAP.keys())
        latest = supported[-1]
        hw_type_map = _HW_TYPES_MAP.get(
            release, _HW_TYPES_MAP[latest])
        return hw_type_map

    def _get_power_adapter_packages(self):
        pkgs = []
        hw_type_map = self._get_hw_type_map()
        for hw_type in self.enabled_hw_types:
            needed_pkgs = hw_type_map.get(
                hw_type, {}).get("needed_packages", [])
            pkgs.extend(needed_pkgs)
        return list(set(pkgs))

    def _get_hardware_types_config(self):
        hw_type_map = self._get_hw_type_map()
        configs = {}
        for hw_type in self.enabled_hw_types:
            details = hw_type_map.get(hw_type, None)
            if details is None:
                # Not a valid hardware type. No need to raise here,
                # we will let the operator know when we validate the
                # config in custom_assess_status_check()
                continue
            driver_cfg = details['config_options']
            for cfg_opt in driver_cfg.items():
                if not configs.get(cfg_opt[0], None):
                    configs[cfg_opt[0]] = cfg_opt[1]
                else:
                    configs[cfg_opt[0]].extend(cfg_opt[1])
                opt_list = list(set(configs[cfg_opt[0]]))
                opt_list.sort()
                configs[cfg_opt[0]] = opt_list

        if self.config.get('use-ipxe', None):
            configs["enabled_boot_interfaces"].append('ipxe')

        # append the noop interfaces at the end
        for noop in _NOOP_INTERFACES:
            if configs.get(noop, None) is not None:
                configs[noop].append(_NOOP_INTERFACES[noop])

        for opt in configs:
            if len(configs[opt]) > 0:
                configs[opt] = ", ".join(configs[opt])
            else:
                configs[opt] = ""
        return configs

    def _setup_power_adapter_config(self):
        pkgs = self._get_power_adapter_packages()
        config = self._get_hardware_types_config()
        self.packages.extend(pkgs)
        self.packages = list(set(self.packages))
        self.config["hardware_type_cfg"] = config

    def _setup_pxe_config(self, cfg):
        self.packages.extend(cfg.determine_packages())
        self.packages = list(set(self.packages))
        self.config["tftpboot"] = cfg.TFTP_ROOT
        self.config["httpboot"] = cfg.HTTP_ROOT
        self.config["ironic_user"] = cfg.IRONIC_USER
        self.config["ironic_group"] = cfg.IRONIC_GROUP
        self.restart_map.update(cfg.get_restart_map())
        if cfg.HTTPD_SERVICE_NAME not in self.services:
            self.services.append(
                cfg.HTTPD_SERVICE_NAME)

    def install(self):
        self.configure_source()
        super().install()
        self.pxe_config._copy_resources()
        self.assess_status()

    def get_amqp_credentials(self):
        """Provide the default amqp username and vhost as a tuple.

        :returns (username, host): two strings to send to the amqp provider.
        """
        return (self.config['rabbit-user'], self.config['rabbit-vhost'])

    def get_database_setup(self):
        return [
            dict(
                database=self.config['database'],
                username=self.config['database-user'], )
        ]

    def _validate_network_interfaces(self, interfaces):
        valid_interfaces = VALID_NETWORK_INTERFACES
        for interface in interfaces:
            if interface not in valid_interfaces:
                raise ValueError(
                    'Network interface %s is not valid. Valid '
                    'interfaces are: %s' % (
                        interface, ", ".join(valid_interfaces)))

    def _validate_default_net_interface(self):
        net_iface = self.config["default-network-interface"]
        if net_iface not in self.enabled_network_interfaces:
            raise ValueError(
                "default-network-interface (%s) is not enabled "
                "in enabled-network-interfaces: %s" % (
                    net_iface,
                    ", ".join(self.enabled_network_interfaces)))

    def _validate_deploy_interfaces(self, interfaces):
        valid_interfaces = VALID_DEPLOY_INTERFACES
        has_secret = reactive.is_flag_set("leadership.set.temp_url_secret")
        for interface in interfaces:
            if interface not in valid_interfaces:
                raise ValueError(
                    'Deploy interface %s is not valid. Valid '
                    'interfaces are: %s' % (
                        interface, ", ".join(valid_interfaces)))
        if reactive.is_flag_set("config.complete"):
            if "direct" in interfaces and has_secret is False:
                raise ValueError(
                    'run set-temp-url-secret action on leader to '
                    'enable direct deploy method')

    def _validate_default_deploy_interface(self):
        iface = self.config["default-deploy-interface"]
        if iface not in self.enabled_deploy_interfaces:
            raise ValueError(
                "default-deploy-interface (%s) is not enabled "
                "in enabled-deploy-interfaces: %s" % (
                    iface, ", ".join(
                        self.enabled_deploy_interfaces)))

    def _validate_enabled_hw_type(self):
        hw_types = self._get_hw_type_map()
        unsupported = []
        for hw_type in self.enabled_hw_types:
            if hw_types.get(hw_type, None) is None:
                unsupported.append(hw_type)
        if len(unsupported) > 0:
            raise ValueError(
                'hardware type(s) %s not supported at '
                'this time' % ", ".join(unsupported))

    @property
    def enabled_network_interfaces(self):
        network_interfaces = self.config.get(
            'enabled-network-interfaces', "").replace(" ", "")
        return network_interfaces.split(",")

    @property
    def enabled_hw_types(self):
        hw_types = self.config.get(
            'enabled-hw-types', "ipmi").replace(" ", "")
        return hw_types.split(",")

    @property
    def enabled_deploy_interfaces(self):
        network_interfaces = self.config.get(
            'enabled-deploy-interfaces', "").replace(" ", "")
        return network_interfaces.split(",")

    def custom_assess_status_check(self):
        try:
            self._validate_network_interfaces(self.enabled_network_interfaces)
        except Exception as err:
            msg = ("invalid enabled-network-interfaces config, %s" % err)
            return ('blocked', msg)

        try:
            self._validate_default_net_interface()
        except Exception as err:
            msg = ("invalid default-network-interface config, %s" % err)
            return ('blocked', msg)

        try:
            self._validate_deploy_interfaces(
                self.enabled_deploy_interfaces)
        except Exception as err:
            msg = ("invalid enabled-deploy-interfaces config, %s" % err)
            return ('blocked', msg)

        try:
            self._validate_default_deploy_interface()
        except Exception as err:
            msg = ("invalid default-deploy-interface config, %s" % err)
            return ('blocked', msg)

        try:
            self._validate_enabled_hw_type()
        except Exception as err:
            msg = ("invalid enabled-hw-types config, %s" % err)
            return ('blocked', msg)

        return (None, None)
