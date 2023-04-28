import src.actions.actions as actions
import unit_tests.test_utils
import reactive.ironic_handlers as handlers
import charm.openstack.ironic.api_utils as api_utils
import charmhelpers.core as ch_core
import charms.leadership as leadership

import mock


class TestActions(unit_tests.test_utils.CharmTestCase):

    def setUp(self):
        super(TestActions, self).setUp()
        self.patches = []
        self.patch_all()
        self.ironic_charm = mock.MagicMock()
        self.patch_object(handlers.charm, 'provide_charm_instance',
                          new=mock.MagicMock())
        self.provide_charm_instance().__enter__.return_value = \
            self.ironic_charm
        self.provide_charm_instance().__exit__.return_value = None

    def test_set_temp_url_secret_keystone_session_successful(self):
        self.patch_object(ch_core.hookenv, 'action_fail')
        self.patch_object(leadership, 'leader_get')

        actions.set_temp_url_secret()

        self.leader_get.assert_called_with('temp_url_secret')

    def test_set_temp_url_secret_keystone_session_exception(self):
        self.patch_object(api_utils, 'create_keystone_session')
        self.patch_object(ch_core.hookenv, 'action_fail')
        self.patch_object(leadership, 'leader_get')

        def raise_exception(*args):
            raise Exception("doh!")

        self.create_keystone_session.side_effect = raise_exception

        actions.set_temp_url_secret()

        self.action_fail.assert_called_with(
            'Failed to create keystone session ("doh!")')
        self.leader_get.assert_not_called()
