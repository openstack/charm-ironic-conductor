from __future__ import absolute_import

import collections
import os

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip
from charms_openstack.adapters import (
    RabbitMQRelationAdapter,
    DatabaseRelationAdapter,
    OpenStackRelationAdapters,
)

import charm.openstack.ironic.controller_utils as controller_utils

PACKAGES = [
    'ironic-conductor',
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

OPENSTACK_RELEASE_KEY = 'ironic-charm.openstack-release-version'


# select the default release function
charms_openstack.charm.use_defaults('charm.default-select-release')


def restart_all():
    IronicConductorCharm.singleton.restart_all()


def assess_status():
    IronicConductorCharm.singleton.assess_status()


def request_endpoint_information(keystone):
    charm = IronicConductorCharm.singleton
    keystone.request_credentials(
        charm.name, region=charm.region)


def request_amqp_access(amqp):
    charm = IronicConductorCharm.singleton
    user, vhost = charm.get_amqp_credentials()
    amqp.request_access(username=user, vhost=vhost)


def setup_database(database):
    charm = IronicConductorCharm.singleton
    for db in charm.get_database_setup():
        database.configure(**db)


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
        ]),
    }

    group = "ironic"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.pxe_config = controller_utils.get_pxe_config_class(
            self.config)
        self.packages.extend(self.pxe_config.determine_packages())
        self._configure_ipxe_webserver()
        self.config["tftpboot"] = self.pxe_config.TFTP_ROOT
        self.config["httpboot"] = self.pxe_config.HTTP_ROOT
        self.config["ironic_user"] = self.pxe_config.IRONIC_USER
        self.config["ironic_group"] = self.pxe_config.IRONIC_GROUP
        self.restart_map.update(self.pxe_config.get_restart_map())
    
    def _configure_ipxe_webserver(self):
        httpd_svc_name = self.pxe_config.HTTPD_SERVICE_NAME
        self.services.append(httpd_svc_name)
        self.restart_map[self.pxe_config.HTTP_SERVER_CONF] = [httpd_svc_name,]

    def upgrade_charm(self):
        self.install()
        super().upgrade_charm()
        self.assess_status()

    def config_changed(self):
        self.install()
        self.pxe_config._copy_resources()
        super().config_changed()
        self.assess_status()

    def install(self):
        self.configure_source()
        super().install()
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