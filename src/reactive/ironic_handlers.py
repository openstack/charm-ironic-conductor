from __future__ import absolute_import

import charms.reactive as reactive
import charmhelpers.core.hookenv as hookenv

import charms_openstack.charm as charm

# Use the charms.openstack defaults for common states and hooks
charm.use_defaults(
    'charm.installed',
    'upgrade-charm',
    'config.changed',
    'update-status',
    'certificates.available')


@reactive.when('shared-db.available')
@reactive.when('ironic-api.available')
@reactive.when('identity-credentials.available')
@reactive.when('amqp.available')
def render(*args):
    hookenv.log("about to call the render_configs with {}".format(args))
    with charm.provide_charm_instance() as ironic_charm:
        ironic_charm.upgrade_if_available(args)
        ironic_charm.render_with_interfaces(
            charm.optional_interfaces(args))
        ironic_charm.configure_tls()
        ironic_charm.assess_status()
    reactive.set_state('config.complete')


@reactive.when('identity-credentials.connected')
def request_keystone_credentials(keystone):
    with charm.provide_charm_instance() as ironic_charm:
        keystone.request_credentials(
            ironic_charm.name, region=ironic_charm.region)
        ironic_charm.assess_status()


@reactive.when('amqp.connected')
def request_amqp_access(amqp):
    with charm.provide_charm_instance() as ironic_charm:
        user, vhost = ironic_charm.get_amqp_credentials()
        amqp.request_access(username=user, vhost=vhost)
        ironic_charm.assess_status()


@reactive.when('shared-db.connected')
def request_database_access(database):
    with charm.provide_charm_instance() as ironic_charm:
        for db in ironic_charm.get_database_setup():
            database.configure(**db)
        ironic_charm.assess_status()
