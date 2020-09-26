import os
import shutil

import charmhelpers.core.host as ch_host


_IRONIC_USER = "ironic"
_IRONIC_GROUP = "ironic"


class PXEBootBase(object):

    TFTP_ROOT = "/tftpboot"
    HTTP_ROOT = "/httpboot"
    HTTP_SERVER_CONF = "/etc/nginx/nginx.conf"
    GRUB_DIR = os.path.join(TFTP_ROOT, "grub")
    GRUB_CFG = os.path.join(GRUB_DIR, "grub.cfg")
    MAP_FILE = os.path.join(TFTP_ROOT, "map-file")
    TFTP_CONFIG = "/etc/default/tftpd-hpa"

    # This is a file map of source to destination. The destination is
    # relative to self.TFTP_ROOT
    FILE_MAP = {
        "/usr/lib/PXELINUX/pxelinux.0": "pxelinux.0",
        "/usr/lib/syslinux/modules/bios/chain.c32": "chain.c32",
        "/usr/lib/syslinux/modules/bios/ldlinux.c32": "ldlinux.c32",
        "/usr/lib/grub/x86_64-efi-signed/grubnetx64.efi.signed": "grubx64.efi",
        "/usr/lib/shim/shimx64.efi.signed": "bootx64.efi",
        "/usr/lib/ipxe/undionly.kpxe": "undionly.kpxe",
        "/usr/lib/ipxe/ipxe.efi": "ipxe.efi",
    }

    TFTP_PACKAGES = ["tftpd-hpa"]
    TFTPD_SERVICE = "tftpd-hpa"
    PACKAGES = [
        'syslinux-common',
        'pxelinux',
        'grub-efi-amd64-signed',
        'shim-signed',
        'ipxe',
    ]
    HTTPD_PACKAGES = ["nginx"]
    HTTPD_SERVICE_NAME = "nginx"
    IRONIC_USER = _IRONIC_USER
    IRONIC_GROUP = _IRONIC_GROUP

    def __init__(self, charm_config):
        self._config = charm_config

    def get_restart_map(self):
        return {
            self.TFTP_CONFIG: [self.TFTPD_SERVICE, ],
            self.MAP_FILE: [self.TFTPD_SERVICE, ],
            self.GRUB_CFG: [self.TFTPD_SERVICE, ],
            self.HTTP_SERVER_CONF: [self.HTTPD_SERVICE_NAME, ],
        }

    def determine_packages(self):
        default_packages = (
            self.PACKAGES + self.TFTP_PACKAGES + self.HTTPD_PACKAGES)
        return default_packages

    def _copy_resources(self):
        self._ensure_folders()
        for f in self.FILE_MAP:
            if os.path.isfile(f) is False:
                raise ValueError(
                    "Missing required file %s. Package not installed?" % f)
            shutil.copy(
                f, os.path.join(self.TFTP_ROOT, self.FILE_MAP[f]),
                follow_symlinks=True)
        ch_host.chownr(
            self.TFTP_ROOT, _IRONIC_USER, _IRONIC_GROUP, chowntopdir=True)

    def _ensure_folders(self):
        if os.path.isdir(self.TFTP_ROOT) is False:
            os.makedirs(self.TFTP_ROOT)

        if os.path.isdir(self.HTTP_ROOT) is False:
            os.makedirs(self.HTTP_ROOT)

        if os.path.isdir(self.GRUB_DIR) is False:
            os.makedirs(self.GRUB_DIR)

        ch_host.chownr(
            self.TFTP_ROOT, _IRONIC_USER, _IRONIC_GROUP, chowntopdir=True)
        ch_host.chownr(
            self.HTTP_ROOT, _IRONIC_USER, _IRONIC_GROUP, chowntopdir=True)


def get_pxe_config_class(charm_config):
    # We may need to make slight adjustments to package names and/or
    # configuration files, based on the version of Ubuntu we are installing
    # on. This function serves as a factory which will return an instance
    # of the proper class to the charm. For now we only have one class.
    return PXEBootBase(charm_config)
