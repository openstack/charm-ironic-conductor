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

import mock

import charms_openstack.test_utils as test_utils
from keystoneauth1 import exceptions as ks_exc

import charm.openstack.ironic.api_utils as api_utils


class _NotFoundException(Exception):
    pass


class TestGetKeystoneSession(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.ks_int = mock.MagicMock()
        self.ks_int.credentials_username.return_value = "ironic"
        self.ks_int.credentials_password.return_value = "super_secret"
        self.ks_int.credentials_project.return_value = "services"
        self.ks_int.auth_protocol.return_value = "https"
        self.ks_int.auth_host.return_value = "example.com"
        self.ks_int.credentials_port.return_value = "5000"
        self.ks_int.api_version.return_value = "3"
        self.ks_int.credentials_project_domain_name.return_value = "default"
        self.ks_int.credentials_user_domain_name.return_value = "default"
        self.ks_expect = {
            "username": "ironic",
            "password": "super_secret",
            "auth_url": "https://example.com:5000",
            "project_name": "services",
            "project_domain_name": "default",
            "user_domain_name": "default",
        }

    def test_create_keystone_session(self):
        self.patch_object(api_utils, 'loading')
        self.patch_object(api_utils, 'ks_session')
        loader = mock.MagicMock()
        auth = mock.MagicMock()
        loader.load_from_options.return_value = auth
        self.loading.get_plugin_loader.return_value = loader
        api_utils.create_keystone_session(self.ks_int)

        self.loading.get_plugin_loader.assert_called_with("v3password")
        loader.load_from_options.assert_called_with(**self.ks_expect)
        self.ks_session.Session.assert_called_with(
            auth=auth, verify=api_utils.SYSTEM_CA_BUNDLE)

    def test_create_keystone_session_v2(self):
        self.patch_object(api_utils, 'loading')
        self.patch_object(api_utils, 'ks_session')
        loader = mock.MagicMock()
        auth = mock.MagicMock()
        loader.load_from_options.return_value = auth
        self.loading.get_plugin_loader.return_value = loader
        self.ks_int.api_version.return_value = "v2.0"
        api_utils.create_keystone_session(self.ks_int)
        del self.ks_expect["project_domain_name"]
        del self.ks_expect["user_domain_name"]

        self.loading.get_plugin_loader.assert_called_with("password")
        loader.load_from_options.assert_called_with(**self.ks_expect)
        self.ks_session.Session.assert_called_with(
            auth=auth, verify=api_utils.SYSTEM_CA_BUNDLE)


class TestOSClients(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.session = mock.MagicMock()
        self.stores = {
            "stores": [
                {"id": "swift"},
                {"id": "local"},
                {"id": "ceph", "default": True}
            ]
        }

        self.patch_object(
            api_utils.glanceclient,
            'Client', name="glance_client")
        self.patch_object(
            api_utils.swiftclient,
            'Connection', name="swift_con")
        self.patch_object(
            api_utils.keystoneclient.v3,
            'Client', name="ks_client")

        self.mocked_glance = mock.MagicMock()
        self.glance_client.return_value = self.mocked_glance
        self.mocked_glance.images.get_stores_info.return_value = self.stores

        self.mocked_swift = mock.MagicMock()
        self.swift_con.return_value = self.mocked_swift

        self.mocked_ks = mock.MagicMock()
        self.ks_client.return_value = self.mocked_ks

        self.target = api_utils.OSClients(self.session)
        self.glance_client.assert_called_with(session=self.session, version=2)
        self.swift_con.assert_called_with(
            session=self.session, cacert=api_utils.SYSTEM_CA_BUNDLE)
        self.ks_client.assert_called_with(session=self.session)

    def test_stores_info(self):
        self.assertEqual(self.target._stores_info, self.stores["stores"])

    def test_glance_stores(self):
        self.assertEqual(
            self.target.glance_stores,
            [i["id"] for i in self.stores["stores"]])

    def test_default_glance_store(self):
        self.assertEqual(self.target.get_default_glance_store(), "ceph")
        del self.stores["stores"][2]["default"]
        self.stores["stores"][1]["default"] = True
        self.assertEqual(self.target.get_default_glance_store(), "local")

    def test_get_object_account_properties(self):
        props = {
            "x-account-meta-fakeprop": "hi there",
            "x-account-meta-fakeprop2": "bye there",
            "bogus": "won't be here in result"
        }
        expected_result = {
            "fakeprop": "hi there",
            "fakeprop2": "bye there",
        }
        self.mocked_swift.get_account.return_value = (props, "")
        result = self.target.get_object_account_properties()
        self.assertEqual(result, expected_result)

    def test_set_object_account_property(self):
        props = {
            "x-account-meta-fakeprop": "hi there",
        }
        self.mocked_swift.get_account.return_value = (props, "")

        self.target.set_object_account_property("FaKePrOp", "hi there")
        self.mocked_swift.post_account.assert_not_called()

        self.target.set_object_account_property("FaKePrOp2", "bye there")
        self.mocked_swift.post_account.assert_called_with(
            {"x-account-meta-fakeprop2": "bye there"})

    def test_delete_object_account_property(self):
        self.target.delete_object_account_property("FaKePrOp2")
        self.mocked_swift.post_account.assert_called_with(
            {"x-account-meta-fakeprop2": ""})

    def test_has_service_type(self):
        mocked_svc_find = mock.MagicMock()
        mocked_svc_find.id = "fakeid"

        self.ks_client.services.find.return_value = mocked_svc_find
        self.target._ks = self.ks_client

        result = self.target._has_service_type(
            "object-store", interface="public")
        self.ks_client.services.find.assert_called_with(
            type="object-store")
        self.ks_client.endpoints.find.assert_called_with(
            service_id="fakeid", interface="public")
        self.assertTrue(result)

    def test_does_not_have_service_type(self):
        ks_exc.http.NotFound = _NotFoundException
        self.ks_client.services.find.side_effect = ks_exc.http.NotFound()
        self.target._ks = self.ks_client

        result = self.target._has_service_type(
            "object-store", interface="public")
        self.ks_client.services.find.assert_called_with(
            type="object-store")
        self.ks_client.endpoints.find.assert_not_called()
        self.assertFalse(result)
