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
import charms.leadership as leadership
import charmhelpers.core.hookenv as hookenv
import charms.reactive as reactive

from charmhelpers.contrib.openstack.utils import os_release

from charm.openstack.ironic import ironic
from charm.openstack.ironic import controller_utils as ctrl_util


class TestIronicCharmConfigProperties(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(ironic.IronicConductorCharm.release)

    def test_deployment_interface_ip(self):
        cls = mock.MagicMock()
        self.patch_object(ironic, 'ch_ip')
        ironic.deployment_interface_ip(cls)
        self.ch_ip.get_relation_ip.assert_called_with('deployment')

    def test_internal_interface_ip(self):
        cls = mock.MagicMock()
        self.patch_object(ironic, 'ch_ip')
        ironic.internal_interface_ip(cls)
        self.ch_ip.get_relation_ip.assert_called_with('internal')

    def test_temp_url_secret(self):
        cls = mock.MagicMock()
        leadership.leader_get.return_value = "fake"
        self.assertEqual(ironic.temp_url_secret(cls), "fake")
        leadership.leader_get.assert_called_with("temp_url_secret")


class TestIronicCharm(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        hookenv.config.return_value = {}
        self.patch_release(ironic.IronicConductorCharm.release)
        self.patch_object(ironic.controller_utils, 'get_pxe_config_class')

        self.mocked_pxe_cfg = mock.MagicMock()
        self.mocked_pxe_cfg.TFTP_ROOT = ctrl_util.PXEBootBase.TFTP_ROOT
        self.mocked_pxe_cfg.HTTP_ROOT = ctrl_util.PXEBootBase.HTTP_ROOT
        self.mocked_pxe_cfg.IRONIC_USER = ctrl_util.PXEBootBase.IRONIC_USER
        self.mocked_pxe_cfg.IRONIC_GROUP = ctrl_util.PXEBootBase.IRONIC_GROUP
        self.mocked_pxe_cfg.determine_packages.return_value = [
            "fakepkg1", "fakepkg2"]
        self.mocked_pxe_cfg.get_restart_map.return_value = {
            "fake_config": [
                "fake_svc", ]}
        self.mocked_pxe_cfg.HTTPD_SERVICE_NAME = "fakehttpd"

        self.get_pxe_config_class.return_value = self.mocked_pxe_cfg

    def test_setup_power_adapter_config_train(self):
        os_release.return_value = "train"
        cfg_data = {
            "enabled-hw-types": "ipmi, redfish, idrac",
        }

        hookenv.config.return_value = cfg_data

        target = ironic.IronicConductorCharm()
        target._setup_power_adapter_config()
        expected = {
            "enabled_hardware_types": "idrac, intel-ipmi, ipmi, redfish",
            "enabled_management_interfaces": ("idrac-redfish, intel-ipmitool, "
                                              "ipmitool, redfish, noop"),
            "enabled_inspect_interfaces": "idrac-redfish, redfish, no-inspect",
            "enabled_power_interfaces": "idrac-redfish, ipmitool, redfish",
            "enabled_console_interfaces": ("ipmitool-shellinabox, "
                                           "ipmitool-socat, no-console"),
            "enabled_raid_interfaces": "idrac-wsman, no-raid",
            "enabled_vendor_interfaces": "idrac-wsman, ipmitool, no-vendor",
            "enabled_boot_interfaces": "pxe",
            "enabled_bios_interfaces": "no-bios"
        }
        self.assertEqual(
            target.config["hardware_type_cfg"],
            expected)

    def test_setup_power_adapter_config_train_ipxe(self):
        os_release.return_value = "train"
        cfg_data = {
            "enabled-hw-types": "ipmi, redfish, idrac",
            "use-ipxe": True,
        }

        hookenv.config.return_value = cfg_data

        target = ironic.IronicConductorCharm()
        target._setup_power_adapter_config()
        expected = {
            "enabled_hardware_types": "idrac, intel-ipmi, ipmi, redfish",
            "enabled_management_interfaces": ("idrac-redfish, intel-ipmitool, "
                                              "ipmitool, redfish, noop"),
            "enabled_inspect_interfaces": "idrac-redfish, redfish, no-inspect",
            "enabled_power_interfaces": "idrac-redfish, ipmitool, redfish",
            "enabled_console_interfaces": ("ipmitool-shellinabox, "
                                           "ipmitool-socat, no-console"),
            "enabled_raid_interfaces": "idrac-wsman, no-raid",
            "enabled_vendor_interfaces": "idrac-wsman, ipmitool, no-vendor",
            "enabled_boot_interfaces": "pxe, ipxe",
            "enabled_bios_interfaces": "no-bios"
        }

        self.assertEqual(
            target.config["hardware_type_cfg"],
            expected)

    def test_setup_power_adapter_config_unknown(self):
        # test that it defaults to latest, in this case ussuri
        os_release.return_value = "unknown"
        cfg_data = {
            "enabled-hw-types": "ipmi, redfish, idrac",
        }

        hookenv.config.return_value = cfg_data

        target = ironic.IronicConductorCharm()
        target._setup_power_adapter_config()
        expected = {
            "enabled_hardware_types": "idrac, intel-ipmi, ipmi, redfish",
            "enabled_management_interfaces": ("idrac-redfish, intel-ipmitool, "
                                              "ipmitool, redfish, noop"),
            "enabled_inspect_interfaces": "idrac-redfish, redfish, no-inspect",
            "enabled_power_interfaces": "idrac-redfish, ipmitool, redfish",
            "enabled_console_interfaces": ("ipmitool-shellinabox, "
                                           "ipmitool-socat, no-console"),
            "enabled_raid_interfaces": "idrac-wsman, no-raid",
            "enabled_vendor_interfaces": "idrac-wsman, ipmitool, no-vendor",
            "enabled_boot_interfaces": "pxe, redfish-virtual-media",
            "enabled_bios_interfaces": "idrac-wsman, no-bios"
        }
        self.assertEqual(
            target.config["hardware_type_cfg"],
            expected)

    def test_setup_power_adapter_config_ussuri(self):
        os_release.return_value = "ussuri"
        cfg_data = {
            "enabled-hw-types": "ipmi, redfish, idrac",
        }

        hookenv.config.return_value = cfg_data

        target = ironic.IronicConductorCharm()
        target._setup_power_adapter_config()
        self.maxDiff = None
        expected = {
            "enabled_hardware_types": "idrac, intel-ipmi, ipmi, redfish",
            "enabled_management_interfaces": ("idrac-redfish, intel-ipmitool, "
                                              "ipmitool, redfish, noop"),
            "enabled_inspect_interfaces": "idrac-redfish, redfish, no-inspect",
            "enabled_power_interfaces": "idrac-redfish, ipmitool, redfish",
            "enabled_console_interfaces": ("ipmitool-shellinabox, "
                                           "ipmitool-socat, no-console"),
            "enabled_raid_interfaces": "idrac-wsman, no-raid",
            "enabled_vendor_interfaces": "idrac-wsman, ipmitool, no-vendor",
            "enabled_boot_interfaces": "pxe, redfish-virtual-media",
            "enabled_bios_interfaces": "idrac-wsman, no-bios"
        }
        self.assertEqual(
            target.config["hardware_type_cfg"],
            expected)

    def test_get_amqp_credentials(self):
        cfg_data = {
            "rabbit-user": "ironic",
            "rabbit-vhost": "openstack",
        }

        hookenv.config.return_value = cfg_data
        target = ironic.IronicConductorCharm()
        self.get_pxe_config_class.assert_called_with(cfg_data)

        result = target.get_amqp_credentials()
        self.assertEqual(result, ('ironic', 'openstack'))

    def test_get_database_setup(self):
        cfg_data = {
            "database-user": "ironic",
            "database": "ironicdb",
        }

        hookenv.config.return_value = cfg_data
        target = ironic.IronicConductorCharm()
        self.get_pxe_config_class.assert_called_with(cfg_data)

        result = target.get_database_setup()
        self.assertEqual(
            result,
            [{
                "database": cfg_data["database"],
                "username": cfg_data["database-user"]}])

    def test_enabled_network_interfaces(self):
        cfg_data = {
            "enabled-network-interfaces": "fake, fake2"}
        hookenv.config.return_value = cfg_data
        target = ironic.IronicConductorCharm()
        self.get_pxe_config_class.assert_called_with(cfg_data)

        self.assertEqual(
            target.enabled_network_interfaces,
            ["fake", "fake2"])

    def test_enabled_deploy_interfaces(self):
        cfg_data = {
            "enabled-deploy-interfaces": "fake, fake2"}
        hookenv.config.return_value = cfg_data
        target = ironic.IronicConductorCharm()
        self.get_pxe_config_class.assert_called_with(cfg_data)

        self.assertEqual(
            target.enabled_deploy_interfaces,
            ["fake", "fake2"])

    def test_configure_defaults_no_cfg(self):
        cfg_data = {
            "default-network-interface": "",
            "default-deploy-interface": ""}
        hookenv.config.return_value = cfg_data
        target = ironic.IronicConductorCharm()
        self.assertEqual(
            target.config.get("default-network-interface"),
            ironic.DEFAULT_NET_IFACE)
        self.assertEqual(
            target.config.get("default-deploy-interface"),
            ironic.DEFAULT_DEPLOY_IFACE)

    def test_configure_defaults_with_user_defined_val(self):
        cfg_data = {
            "default-network-interface": "fake_net",
            "default-deploy-interface": "fake_deploy"}

        hookenv.config.return_value = cfg_data
        target = ironic.IronicConductorCharm()
        target._configure_defaults()

        self.assertEqual(
            target.config.get("default-network-interface"),
            "fake_net")
        self.assertEqual(
            target.config.get("default-deploy-interface"),
            "fake_deploy")

    def test_setup_pxe_config(self):
        hookenv.config.return_value = {
            "default-network-interface": "fake_net",
            "default-deploy-interface": "fake_deploy"}

        target = ironic.IronicConductorCharm()
        target._setup_pxe_config(self.mocked_pxe_cfg)
        expected_pkgs = ironic.PACKAGES + ["fakepkg1", "fakepkg2"]

        expected_cfg = {
            'tftpboot': ctrl_util.PXEBootBase.TFTP_ROOT,
            'httpboot': ctrl_util.PXEBootBase.HTTP_ROOT,
            'ironic_user': ctrl_util.PXEBootBase.IRONIC_USER,
            'ironic_group': ctrl_util.PXEBootBase.IRONIC_GROUP,
            'hardware_type_cfg': {
                'enabled_hardware_types': 'intel-ipmi, ipmi',
                'enabled_management_interfaces': ('intel-ipmitool, ipmitool,'
                                                  ' noop'),
                'enabled_inspect_interfaces': 'no-inspect',
                'enabled_power_interfaces': 'ipmitool',
                'enabled_console_interfaces': ('ipmitool-shellinabox, '
                                               'ipmitool-socat, no-console'),
                'enabled_raid_interfaces': 'no-raid',
                'enabled_vendor_interfaces': 'ipmitool, no-vendor',
                'enabled_boot_interfaces': 'pxe',
                'enabled_bios_interfaces': 'no-bios'},
            'default-network-interface': 'fake_net',
            'default-deploy-interface': 'fake_deploy'}

        self.assertEqual(
            target.packages.sort(),
            expected_pkgs.sort())
        self.assertEqual(target.config, expected_cfg)
        self.assertEqual(
            target.restart_map.get("fake_config", []), ["fake_svc"])
        self.assertTrue("fakehttpd" in target.services)

    def test_validate_network_interfaces(self):
        target = ironic.IronicConductorCharm()
        with self.assertRaises(ValueError):
            target._validate_network_interfaces(["bogus"])
        self.assertIsNone(
            target._validate_network_interfaces(["neutron"]))

    def test_validate_deploy_interfaces(self):
        target = ironic.IronicConductorCharm()
        with self.assertRaises(ValueError) as err:
            target._validate_deploy_interfaces(["bogus"])

        expected_msg = (
            'Deploy interface bogus is not valid.'
            ' Valid interfaces are: direct, iscsi')

        self.assertIsNone(
            target._validate_deploy_interfaces(["direct"]))
        self.assertEqual(str(err.exception), expected_msg)

    def test_validate_deploy_interfaces_tmp_secret(self):
        # leadership.set.temp_url_secret is not set, and "direct"
        # boot method is enabled. Validate will fail, until
        # set-temp-url-secret action is run
        reactive.is_flag_set.side_effect = [False, True]
        target = ironic.IronicConductorCharm()
        with self.assertRaises(ValueError) as err:
            target._validate_deploy_interfaces(["direct"])
        expected_msg = (
            'run set-temp-url-secret action on '
            'leader to enable direct deploy method')
        self.assertEqual(str(err.exception), expected_msg)

    def test_validate_default_net_interface(self):
        hookenv.config.return_value = {
            "default-network-interface": "flat",
            "enabled-network-interfaces": "neutron, flat, noop"}
        target = ironic.IronicConductorCharm()
        self.assertIsNone(target._validate_default_net_interface())

    def test_validate_default_net_interface_invalid_default(self):
        hookenv.config.return_value = {
            "default-network-interface": "bogus",
            "enabled-network-interfaces": "neutron, flat, noop"}
        target = ironic.IronicConductorCharm()
        with self.assertRaises(ValueError) as err:
            target._validate_default_net_interface()

        expected_msg = (
            "default-network-interface (bogus) is not enabled "
            "in enabled-network-interfaces: neutron, flat, noop")
        self.assertEqual(str(err.exception), expected_msg)

    def test_validate_default_deploy_interface(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "direct",
            "enabled-deploy-interfaces": "direct, iscsi"}
        target = ironic.IronicConductorCharm()
        self.assertIsNone(target._validate_default_deploy_interface())

    def test_validate_default_deploy_interface_invalid_default(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "bogus",
            "enabled-deploy-interfaces": "direct, iscsi"}
        target = ironic.IronicConductorCharm()
        with self.assertRaises(ValueError) as err:
            target._validate_default_deploy_interface()

        expected_msg = (
            "default-deploy-interface (bogus) is not enabled "
            "in enabled-deploy-interfaces: direct, iscsi")
        self.assertEqual(str(err.exception), expected_msg)

    def test_custom_assess_status_check_all_good(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "direct",
            "enabled-deploy-interfaces": "direct, iscsi",
            "default-network-interface": "flat",
            "enabled-network-interfaces": "neutron, flat, noop"}
        target = ironic.IronicConductorCharm()
        self.assertEqual(target.custom_assess_status_check(), (None, None))

    def test_custom_assess_status_check_invalid_enabled_net_ifaces(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "direct",
            "enabled-deploy-interfaces": "direct, iscsi",
            "default-network-interface": "flat",
            "enabled-network-interfaces": "bogus, noop"}
        target = ironic.IronicConductorCharm()
        expected_status = (
            'blocked',
            'invalid enabled-network-interfaces config, Network interface '
            'bogus is not valid. Valid interfaces are: neutron, flat, noop'
        )
        self.assertEqual(target.custom_assess_status_check(), expected_status)

    def test_custom_assess_status_check_invalid_enabled_deploy_ifaces(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "direct",
            "enabled-deploy-interfaces": "bogus, iscsi",
            "default-network-interface": "flat",
            "enabled-network-interfaces": "neutron, flat, noop"}
        target = ironic.IronicConductorCharm()
        expected_status = (
            'blocked',
            'invalid enabled-deploy-interfaces config, Deploy interface '
            'bogus is not valid. Valid interfaces are: direct, iscsi'
        )
        self.assertEqual(target.custom_assess_status_check(), expected_status)

    def test_custom_assess_status_check_invalid_default_net_iface(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "direct",
            "enabled-deploy-interfaces": "direct, iscsi",
            "default-network-interface": "bogus",
            "enabled-network-interfaces": "neutron, flat, noop"}
        target = ironic.IronicConductorCharm()
        expected_status = (
            'blocked',
            'invalid default-network-interface config, '
            'default-network-interface (bogus) is not enabled '
            'in enabled-network-interfaces: neutron, flat, noop'
        )
        self.assertEqual(target.custom_assess_status_check(), expected_status)

    def test_custom_assess_status_check_invalid_default_deploy_iface(self):
        hookenv.config.return_value = {
            "default-deploy-interface": "bogus",
            "enabled-deploy-interfaces": "direct, iscsi",
            "default-network-interface": "flat",
            "enabled-network-interfaces": "neutron, flat, noop"}
        target = ironic.IronicConductorCharm()
        expected_status = (
            'blocked',
            'invalid default-deploy-interface config, default-deploy-interface'
            ' (bogus) is not enabled in enabled-deploy-interfaces: direct, '
            'iscsi')
        self.assertEqual(target.custom_assess_status_check(), expected_status)
