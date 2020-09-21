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

import charm.openstack.ironic.controller_utils as controller_utils
import charms_openstack.adapters as adapters
import charmhelpers.contrib.network.ip as ch_ip
import charms.leadership as leadership
import charms.reactive as reactive

PACKAGES = [
    'ironic-conductor',
    'python3-keystoneauth1',
    'python3-keystoneclient',
    'python3-glanceclient',
    'python3-swiftclient',
    'python-mysqldb',
    'python3-dracclient',
    'python3-sushy',
    'python3-ironicclient',
    'python3-scciclient',
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
def temp_url_secret(self):
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
    mandatory_config = []

    def __init__(self, **kw):
        super().__init__(**kw)
        self.pxe_config = controller_utils.get_pxe_config_class(
            self.config)
        self._setup_pxe_config(self.pxe_config)
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

    def _setup_pxe_config(self, cfg):
        self.packages.extend(cfg.determine_packages())
        self.config["tftpboot"] = cfg.TFTP_ROOT
        self.config["httpboot"] = cfg.HTTP_ROOT
        self.config["ironic_user"] = cfg.IRONIC_USER
        self.config["ironic_group"] = cfg.IRONIC_GROUP
        self.restart_map.update(cfg.get_restart_map())
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
                    'Network interface "%s" is not valid. Valid '
                    'interfaces are: %s' % (
                        interface, ", ".join(valid_interfaces)))

    def _validate_default_net_interface(self):
        net_iface = self.config["default-network-interface"]
        if net_iface not in self.enabled_network_interfaces:
            raise ValueError(
                "default-network-interface (%s) is not enabled "
                "in enabled-network-interfaces: %s" % ", ".join(
                    self.enabled_network_interfaces))

    def _validate_deploy_interfaces(self, interfaces):
        valid_interfaces = VALID_DEPLOY_INTERFACES
        has_secret = reactive.is_flag_set("leadership.set.temp_url_secret")
        for interface in interfaces:
            if interface not in valid_interfaces:
                raise ValueError(
                    "Deploy interface %s is not valid. Valid "
                    "interfaces are: %s" % (
                        interface, ", ".join(valid_interfaces)))
        if reactive.is_flag_set("config.complete"):
            if "direct" in interfaces and has_secret is False:
                raise ValueError(
                    'run "set-temp-url-secret" action on leader to '
                    'enable "direct" deploy method')

    def _validate_default_deploy_interface(self):
        iface = self.config["default-deploy-interface"]
        if iface not in self.enabled_deploy_interfaces:
            raise ValueError(
                "default-deploy-interface (%s) is not enabled "
                "in enabled-deploy-interfaces: %s" % ", ".join(
                    self.enabled_deploy_interfaces))

    @property
    def enabled_network_interfaces(self):
        network_interfaces = self.config.get(
            'enabled-network-interfaces', "").replace(" ", "")
        return network_interfaces.split(",")

    @property
    def enabled_deploy_interfaces(self):
        network_interfaces = self.config.get(
            'enabled-deploy-interfaces', "").replace(" ", "")
        return network_interfaces.split(",")

    def custom_assess_status_check(self):
        try:
            self._validate_network_interfaces(self.enabled_network_interfaces)
        except Exception as err:
            msg = ("invalid enabled-network-interfaces config: %s" % err)
            return ('blocked', msg)

        try:
            self._validate_default_net_interface()
        except Exception as err:
            msg = ("invalid default-network-interface config: %s" % err)
            return ('blocked', msg)

        try:
            self._validate_deploy_interfaces(
                self.enabled_deploy_interfaces)
        except Exception as err:
            msg = ("invalid enabled-deploy-interfaces config: %s" % err)
            return ('blocked', msg)

        try:
            self._validate_default_deploy_interface()
        except Exception as err:
            msg = ("invalid default-deploy-interface config: %s" % err)
            return ('blocked', msg)
        return (None, None)
