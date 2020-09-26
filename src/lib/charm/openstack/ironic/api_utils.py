from keystoneauth1 import loading
from keystoneauth1 import session as ks_session
from keystoneauth1 import exceptions as ks_exc

import glanceclient
import swiftclient
import keystoneclient

SYSTEM_CA_BUNDLE = '/etc/ssl/certs/ca-certificates.crt'


def create_keystone_session(keystone):
    plugin_name = "password"
    username = keystone.credentials_username()
    password = keystone.credentials_password()

    plugin_args = {
        "username": username,
        "password": password,
    }

    project_name = keystone.credentials_project()

    auth_url = "%s://%s:%s" % (
        keystone.auth_protocol(),
        keystone.auth_host(),
        keystone.credentials_port())

    plugin_args.update({
        "auth_url": auth_url,
        "project_name": project_name,
    })

    keystone_version = keystone.api_version()
    if keystone_version and str(keystone_version) == "3":
        plugin_name = "v3" + plugin_name

        project_domain_name = keystone.credentials_project_domain_name()
        plugin_args["project_domain_name"] = project_domain_name

        user_domain_name = keystone.credentials_user_domain_name()
        plugin_args["user_domain_name"] = user_domain_name

    loader = loading.get_plugin_loader(plugin_name)
    auth = loader.load_from_options(**plugin_args)
    return ks_session.Session(auth=auth, verify=SYSTEM_CA_BUNDLE)


class OSClients(object):

    def __init__(self, session):
        self._session = session
        self._img_cli = glanceclient.Client(
            session=self._session, version=2)
        self._obj_cli = swiftclient.Connection(
            session=self._session, cacert=SYSTEM_CA_BUNDLE)
        self._ks = keystoneclient.v3.Client(
            session=session)
        self._stores = None

    @property
    def _stores_info(self):
        if self._stores:
            return self._stores
        store = self._img_cli.images.get_stores_info()
        self._stores = store.get(
            "stores", [])
        return self._stores

    @property
    def glance_stores(self):
        return [stor["id"] for stor in self._stores_info]

    def get_default_glance_store(self):
        for stor in self._stores_info:
            if stor.get("default"):
                return stor["id"]
        raise ValueError("no default store set")

    def get_object_account_properties(self):
        acct = self._obj_cli.get_account()
        props = {}
        for prop, val in acct[0].items():
            if prop.startswith('x-account-meta-'):
                props[prop.replace("x-account-meta-", "")] = val
        return props

    def set_object_account_property(self, prop, value):
        current_props = self.get_object_account_properties()
        prop = prop.lower()
        if current_props.get(prop, None) == value:
            return
        meta_key = 'x-account-meta-%s' % prop
        headers = {
            meta_key: value}
        self._obj_cli.post_account(headers)

    def delete_object_account_property(self, prop):
        prop = prop.lower()
        meta_key = 'x-account-meta-%s' % prop
        headers = {
            meta_key: ''}
        self._obj_cli.post_account(headers)

    def _has_service_type(self, svc_type, interface="public"):
        try:
            svc = self._ks.services.find(type=svc_type)
            self._ks.endpoints.find(
                service_id=svc.id, interface=interface)
        except ks_exc.http.NotFound:
            return False
        return True

    def has_swift(self):
        return self._has_service_type("object-store")

    def has_glance(self):
        return self._has_service_type("image")
