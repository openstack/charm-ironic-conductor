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

import json
import mock

from charm.openstack.ironic import ironic
import reactive.ironic_handlers as handlers

import charms_openstack.test_utils as test_utils


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = [
            'charm.installed',
            'config.changed',
            'update-status',
            'upgrade-charm',
        ]
        hook_set = {
            'when': {
                'render': ('shared-db.available',
                           'ironic-api.available',
                           'identity-credentials.available',
                           'amqp.available',),
                'request_keystone_credentials': (
                    'identity-credentials.connected',),
                'request_amqp_access': (
                    'amqp.connected',),
                'request_database_access': (
                    'shared-db.connected',),
            },
            'hook': {
                'upgrade_charm': ('upgrade-charm',),
            },
        }
        # test that the hooks were registered via the
        # reactive.ironic_handlers
        self.registered_hooks_test_helper(handlers, hook_set, defaults)


class TestIronicHandlers(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(ironic.IronicConductorCharm.release)
        self.ironic_charm = mock.MagicMock()
        self.patch_object(handlers.charm, 'provide_charm_instance',
                          new=mock.MagicMock())
        self.provide_charm_instance().__enter__.return_value = \
            self.ironic_charm
        self.provide_charm_instance().__exit__.return_value = None

    def test_request_keystone_credentials(self):
        keystone = mock.MagicMock()
        handlers.request_keystone_credentials(keystone)
        keystone.request_credentials.assert_called_once_with(
            self.ironic_charm.name,
            region=self.ironic_charm.region)
        self.ironic_charm.assess_status.assert_called_once_with()

    def test_render(self):
        self.patch('charms.reactive.set_state', 'set_state')
        self.patch_object(handlers.charm, 'optional_interfaces')
        self.optional_interfaces.return_value = ('fake', 'interface', 'list')
        handlers.render('arg1', 'arg2')
        self.ironic_charm.render_with_interfaces.assert_called_once_with(
            ('fake', 'interface', 'list'))
        self.optional_interfaces.assert_called_once_with(
            ('arg1', 'arg2'))
        self.ironic_charm.configure_tls.assert_called_once_with()
        self.ironic_charm.assess_status.assert_called_once_with()
        self.set_state.assert_called_once_with('config.complete')

    def test_request_amqp_access(self):
        amqp = mock.MagicMock()
        config = {
            'rabbit-user': 'ironic',
            'rabbit-vhost': 'openstack',
        }
        self.ironic_charm.get_amqp_credentials.return_value = list(
            config.values()) 
        handlers.request_amqp_access(amqp)
        amqp.request_access.assert_called_once_with(
            username=config['rabbit-user'],
            vhost=config['rabbit-vhost'])
        self.ironic_charm.assess_status.assert_called_once_with()

    def test_request_database_access(self):
        database = mock.MagicMock()
        dbs = [{
            "database": "ironic",
            "username": "ironic",
        },
        # Ironic only needs one DB, but the code can handle more,
        # so we test it.
        {
            "database": "second_db",
            "username": "second_user",
        }]
        self.ironic_charm.get_database_setup.return_value = dbs
        calls = [mock.call(**i) for i in dbs]

        handlers.request_database_access(database)
        database.configure.assert_has_calls(calls, any_order=True)
        self.ironic_charm.assess_status.assert_called_once_with()
