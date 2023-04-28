#!/usr/local/sbin/charm-env python3
# Copyright 2020 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import os
import sys
import traceback
import uuid

# Load modules from $CHARM_DIR/lib
sys.path.append('lib')
sys.path.append('reactive')

from charms.layer import basic
basic.bootstrap_charm_deps()
basic.init_config_states()

import charms.reactive as reactive
import charms.leadership as leadership

import charms_openstack.bus
import charms_openstack.charm as charm

import charmhelpers.core as ch_core

import charm.openstack.ironic.api_utils as api_utils

charms_openstack.bus.discover()


def set_temp_url_secret(*args):
    """Set Temp-Url-Key on storage account"""
    if not reactive.is_flag_set('leadership.is_leader'):
        return ch_core.hookenv.action_fail('action must be run on the leader '
                                           'unit.')
    if not reactive.is_flag_set('config.complete'):
        return ch_core.hookenv.action_fail('required relations are not yet '
                                           'available, please defer action'
                                           'until deployment is complete.')
    identity_service = reactive.endpoint_from_flag(
        'identity-credentials.available')
    try:
        keystone_session = api_utils.create_keystone_session(identity_service)
    except Exception as e:
        ch_core.hookenv.action_fail('Failed to create keystone session ("{}")'
                                    .format(e))
        return

    os_cli = api_utils.OSClients(keystone_session)
    if os_cli.has_swift() is False:
        ch_core.hookenv.action_fail(
            'Swift not yet available. Please wait for deployment to finish')

    if os_cli.has_glance() is False:
        ch_core.hookenv.action_fail(
            'Glance not yet available. Please wait for deployment to finish')

    if "swift" not in os_cli.glance_stores:
        ch_core.hookenv.action_fail(
            'Glance does not support Swift storage backend. '
            'Please add relation between glance and ceph-radosgw/swift')

    current_secret = leadership.leader_get("temp_url_secret")
    current_swift_secret = os_cli.get_object_account_properties().get(
        'temp-url-key', None)

    if not current_secret or current_swift_secret != current_secret:
        secret = hashlib.sha1(
            str(uuid.uuid4()).encode()).hexdigest()
        os_cli.set_object_account_property("temp-url-key", secret)
        leadership.leader_set({"temp_url_secret": secret})
        # render configs on leader, and assess status. Every other unit
        # will render theirs when leader-settings-changed executes.
        shared_db = reactive.endpoint_from_flag(
            'shared-db.available')
        ironic_api = reactive.endpoint_from_flag(
            'ironic-api.available')
        amqp = reactive.endpoint_from_flag(
            'amqp.available')

        with charm.provide_charm_instance() as ironic_charm:
            ironic_charm.render_with_interfaces(
                charm.optional_interfaces(
                    (identity_service, shared_db, ironic_api, amqp)))
            ironic_charm._assess_status()


ACTIONS = {
    'set-temp-url-secret': set_temp_url_secret,
}


def main(args):
    action_name = os.path.basename(args[0])
    try:
        action = ACTIONS[action_name]
    except KeyError:
        return 'Action {} undefined'.format(action_name)
    else:
        try:
            action(args)
        except Exception as e:
            ch_core.hookenv.log('action "{}" failed: "{}" "{}"'
                                .format(action_name, str(e),
                                        traceback.format_exc()),
                                level=ch_core.hookenv.ERROR)
            ch_core.hookenv.action_fail(str(e))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
