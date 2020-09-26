import sys
import mock

sys.path.append('src')
sys.path.append('src/lib')

# Mock out charmhelpers so that we can test without it.
import charms_openstack.test_mocks  # noqa
charms_openstack.test_mocks.mock_charmhelpers()
sys.modules['charmhelpers.core.decorators'] = (
    charms_openstack.test_mocks.charmhelpers.core.decorators)


class _fake_decorator(object):

    def __init__(self, *args):
        pass

    def __call__(self, f):
        return f


charms = mock.MagicMock()
sys.modules['charms'] = charms
charms.leadership = mock.MagicMock()
sys.modules['charms.leadership'] = charms.leadership
charms.reactive = mock.MagicMock()
charms.reactive.when = _fake_decorator
charms.reactive.when_all = _fake_decorator
charms.reactive.when_any = _fake_decorator
charms.reactive.when_not = _fake_decorator
charms.reactive.when_none = _fake_decorator
charms.reactive.when_not_all = _fake_decorator
charms.reactive.not_unless = _fake_decorator
charms.reactive.when_file_changed = _fake_decorator
charms.reactive.collect_metrics = _fake_decorator
charms.reactive.meter_status_changed = _fake_decorator
charms.reactive.only_once = _fake_decorator
charms.reactive.hook = _fake_decorator
charms.reactive.bus = mock.MagicMock()
charms.reactive.flags = mock.MagicMock()
charms.reactive.relations = mock.MagicMock()
sys.modules['charms.reactive'] = charms.reactive
sys.modules['charms.reactive.bus'] = charms.reactive.bus
sys.modules['charms.reactive.bus'] = charms.reactive.decorators
sys.modules['charms.reactive.flags'] = charms.reactive.flags
sys.modules['charms.reactive.relations'] = charms.reactive.relations

keystoneauth1 = mock.MagicMock()
sys.modules['keystoneauth1'] = keystoneauth1

glanceclient = mock.MagicMock()
sys.modules['glanceclient'] = glanceclient

swiftclient = mock.MagicMock()
sys.modules['swiftclient'] = swiftclient

keystoneclient = mock.MagicMock()
sys.modules['keystoneclient'] = keystoneclient
