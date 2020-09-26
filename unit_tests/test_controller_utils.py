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

import os
import mock
import shutil

import charms_openstack.test_utils as test_utils
import charmhelpers.core.host as ch_host

import charm.openstack.ironic.controller_utils as controller_utils


class TestGetPXEBootClass(test_utils.PatchHelper):

    def test_get_pxe_config_class(self):
        self.patch_object(
            ch_host, 'get_distrib_codename')
        self.get_distrib_codename.return_value = "focal"
        charm_config = {}
        pxe_class = controller_utils.get_pxe_config_class(charm_config)
        self.assertTrue(
            isinstance(
                pxe_class, controller_utils.PXEBootBase))


class TestPXEBootBase(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.target = controller_utils.PXEBootBase({})

    def test_ensure_folders(self):
        global _TEST_FOLDERS
        self.patch_object(os.path, 'isdir')
        self.isdir.side_effect = [False, False, False]
        self.patch_object(os, 'makedirs')
        self.patch_object(ch_host, 'chownr')
        self.target._ensure_folders()
        chown_call_list = [
            mock.call(
                controller_utils.PXEBootBase.TFTP_ROOT,
                controller_utils._IRONIC_USER,
                controller_utils._IRONIC_GROUP,
                chowntopdir=True),
            mock.call(
                controller_utils.PXEBootBase.HTTP_ROOT,
                controller_utils._IRONIC_USER,
                controller_utils._IRONIC_GROUP,
                chowntopdir=True),
        ]
        isdir_call_list = [
            mock.call(controller_utils.PXEBootBase.TFTP_ROOT),
            mock.call(controller_utils.PXEBootBase.HTTP_ROOT),
            mock.call(controller_utils.PXEBootBase.GRUB_DIR),
        ]

        makedirs_call_list = [
            mock.call(controller_utils.PXEBootBase.TFTP_ROOT),
            mock.call(controller_utils.PXEBootBase.HTTP_ROOT),
            mock.call(controller_utils.PXEBootBase.GRUB_DIR),
        ]
        self.isdir.assert_has_calls(isdir_call_list)
        self.makedirs.assert_has_calls(makedirs_call_list)
        ch_host.chownr.assert_has_calls(chown_call_list)

    def test_copy_resources_missing_file(self):
        self.patch_object(self.target, '_ensure_folders')
        self.patch_object(os.path, 'isfile')
        is_file_returns = list([
            True for i in controller_utils.PXEBootBase.FILE_MAP])
        is_file_returns[0] = False
        self.isfile.side_effect = is_file_returns
        with self.assertRaises(ValueError):
            self.target._copy_resources()

    def test_copy_resources(self):
        shutil_calls = [
            mock.call(
                i,
                os.path.join(
                    controller_utils.PXEBootBase.TFTP_ROOT,
                    controller_utils.PXEBootBase.FILE_MAP[i]),
                follow_symlinks=True
            ) for i in controller_utils.PXEBootBase.FILE_MAP
        ]
        self.patch_object(self.target, '_ensure_folders')
        self.patch_object(os.path, 'isfile')
        self.patch_object(shutil, 'copy')
        self.patch_object(ch_host, 'chownr')
        self.isfile.side_effect = [
            True for i in controller_utils.PXEBootBase.FILE_MAP]

        self.target._copy_resources()
        self._ensure_folders.assert_called_with()
        self.copy.assert_has_calls(shutil_calls)
        self.chownr.assert_called_with(
            controller_utils.PXEBootBase.TFTP_ROOT,
            controller_utils._IRONIC_USER,
            controller_utils._IRONIC_GROUP,
            chowntopdir=True)
