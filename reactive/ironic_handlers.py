from __future__ import absolute_import

import charms.reactive as reactive
import charmhelpers.core.hookenv as hookenv

import charms_openstack.charm as charm
import charm.openstack.ironic.ironic as ironic  # noqa

from charmhelpers.core.templating import render
import charmhelpers.contrib.network.ip as ch_ip
import charms_openstack.adapters as adapters


# Use the charms.openstack defaults for common states and hooks
charm.use_defaults(
    'charm.installed',
    'upgrade-charm',
    'config.changed',
    'update-status')


@reactive.when('shared-db.available')
@reactive.when('identity-credentials.available')
@reactive.when('amqp.available')
def render_stuff(*args):
    hookenv.log("about to call the render_configs with {}".format(args))
    with charm.provide_charm_instance() as ironic_charm:
        ironic_charm.render_with_interfaces(
            charm.optional_interfaces(args))
        ironic_charm.assess_status()
    reactive.set_state('config.complete')


@reactive.when('identity-credentials.connected')
def setup_endpoint(keystone):
    ironic.request_endpoint_information(keystone)
    ironic.assess_status()

@reactive.when('amqp.connected')
def request_amqp_access(amqp):
    ironic.request_amqp_access(amqp)
    ironic.assess_status()


@reactive.when('shared-db.connected')
def setup_database(database):
    ironic.setup_database(database)
    ironic.assess_status()


@adapters.config_property
def deployment_interface_ip(args):
    return ch_ip.get_relation_ip("deployment")


@adapters.config_property
def internal_interface_ip(args):
    return ch_ip.get_relation_ip("internal")
