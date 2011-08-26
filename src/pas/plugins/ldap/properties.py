import os
import copy
import json
import ldap
from odict import odict
from node.ext.ldap.scope import (
    BASE,
    ONELEVEL,
    SUBTREE,
)
from node.ext.ldap.interfaces import (
    ILDAPProps,
    ILDAPUsersConfig,
    ILDAPGroupsConfig,
)
from node.ext.ldap.ugm import Ugm
from zope.interface import implements
from zope.component import adapts
import yafowil.zope2
from yafowil.base import UNSET
from yafowil.controller import Controller
from yafowil.yaml import parse_from_YAML
from zope.i18nmessageid import MessageFactory
from zExceptions import Redirect
from Products.Five import BrowserView
from .interfaces import ILDAPPlugin

_ = MessageFactory('pas.plugins.ldap')

class BasePropertiesForm(BrowserView):
    
    yaml = os.path.join(os.path.dirname(__file__), 'properties.yaml')

    scope_vocab = [
        (str(BASE), 'BASE'),
        (str(ONELEVEL), 'ONELEVEL'),
        (str(SUBTREE), 'SUBTREE'),
    ]
    
    static_attrs = ['rdn', 'id', 'login']

    @property
    def plugin(self):
        raise NotImplementedError()

    def next(self, request):
        raise NotImplementedError()

    @property
    def action(self):
        raise NotImplementedError()


    def form(self):
        # make configuration data available on form context
        self.props =  ILDAPProps(self.plugin)
        self.users =  ILDAPUsersConfig(self.plugin)
        self.groups = ILDAPGroupsConfig(self.plugin)

        # prepare users data on form context
        self.users_attrmap = odict()
        for key in self.static_attrs:
            self.users_attrmap[key] = self.users.attrmap.get(key)
        
        self.users_propsheet_attrmap = odict()
        for key, value in self.users.attrmap.items():
            if key in self.static_attrs:
                continue
            self.users_propsheet_attrmap[key] = value

        # prepare groups data on form context
        self.groups_attrmap = odict()
        for key in self.static_attrs:
            self.groups_attrmap[key] = self.groups.attrmap.get(key)
        self.groups_propsheet_attrmap = odict()
        for key, value in self.groups.attrmap.items():
            if key in self.static_attrs:
                continue
            self.groups_propsheet_attrmap[key] = value

        # handle form
        form = parse_from_YAML(self.yaml, self,  _)
        controller = Controller(form, self.request)
        if not controller.next:
            return controller.rendered
        raise Redirect(controller.next)    

    
    def save(self, widget, data):
        props =  ILDAPProps(self.plugin)
        users =  ILDAPUsersConfig(self.plugin)
        groups = ILDAPGroupsConfig(self.plugin)
        def fetch(name):
            name = 'ldapsettings.%s' % name
            return data.fetch(name).extracted
        props.uri = fetch('server.uri')
        props.user = fetch('server.user')
        password = fetch('server.password')
        if password is not UNSET:
            props.password = password
        # XXX: later
        #props.cache = fetch('cache')
        #props.timeout = fetch('timeout')
        #props.start_tls = fetch('start_tls')
        #props.tls_cacertfile = fetch('tls_cacertfile')
        #props.tls_cacertdir = fetch('tls_cacertdir')
        #props.tls_clcertfile = fetch('tls_clcertfile')
        #props.tls_clkeyfile = fetch('tls_clkeyfile')
        #props.retry_max = fetch(at('retry_max')
        #props.retry_delay = fetch('retry_delay')
        users.baseDN = fetch('users.dn')
        map = odict()
        map.update(fetch('users.aliases_attrmap'))
        users_propsheet_attrmap = fetch('users.propsheet_attrmap')
        if users_propsheet_attrmap is not UNSET:
            map.update(users_propsheet_attrmap)
        users.attrmap = map
        users.scope = fetch(at('users.scope')).extracted
        users.queryFilter = fetch('users.query')
        objectClasses = fetch('users.object_classes')
        objectClasses = \
            [v.strip() for v in objectClasses.split(',') if v.strip()]
        users.objectClasses = objectClasses
        groups = self.groups
        groups.baseDN = fetch('groups.dn')
        map = odict()
        map.update(fetch('groups.aliases_attrmap'))
        groups_propsheet_attrmap = fetch('groups.propsheet_attrmap')
        if groups_propsheet_attrmap is not UNSET:
            map.update(groups_propsheet_attrmap)
        groups.attrmap = map
        groups.scope = fetch('groups.scope')
        groups.queryFilter = fetch('groups.query')
        objectClasses = fetch('groups.object_classes')
        objectClasses = \
            [v.strip() for v in objectClasses.split(',') if v.strip()]
        groups.objectClasses = objectClasses       
        
    def connection_test(self):
        props =  ILDAPProps(self.plugin)
        users =  ILDAPUsersConfig(self.plugin)
        groups = ILDAPGroupsConfig(self.plugin)
        ugm = Ugm('test', props=props, ucfg=users, gcfg=groups)
        try:
            ugm.users
        except ldap.SERVER_DOWN, e:
            return False, _("Server Down")
        except ldap.LDAPError, e:
            return False, _('LDAP users; ') + e.message['desc']
        except Exception, e:
            return False, _('Other; ') + str(e)
        try:
            ugm.groups
        except ldap.LDAPError, e:
            return False, _('LDAP groups; ') + e.message['desc']
        except Exception, e:
            return False, _('Other; ') + str(e)
        return True, 'Connection, users- and groups-access tested successfully.'         

TLDAP = 'ldapprops'
TUSERS = 'usersconfig'
TGROUPS = 'groupsconfig'
STORAGES = [TLDAP, TUSERS, TGROUPS]                    

class PropProxy(object):
    
    def __init__(self, proptype, key, default=None, json=False):
        self.proptype = proptype
        self.key = key
        self.default = copy.copy(default)
        self.json = json
        

    def __call__(self):
        def _getter(context):
            props = getattr(context.plugin, self.proptype, None)
            if not props:
                value = self.default
            else:
                value = props.get(self.key, self.default)
            if self.json:
                return json.loads(value)
            return value
        def _setter(context, value):
            if self.json:
                value = json.dumps(value)
            plugin = context.plugin
            for storage in STORAGES: 
                if not hasattr(plugin, storage):
                    setattr(plugin, storage, PersistentDict())
            props = getattr(plugin, self.proptype)
            props[self.key] = value
        return property(_getter, _setter)

class LDAPProps(object):

    implements(ILDAPProps)
    adapts(ILDAPPlugin)
    
    def __init__(self, plugin):
        self.plugin = plugin

    uri = PropProxy(TLDAP, 'uri', '')()
    user = PropProxy(TLDAP, 'user', '')()
    password = PropProxy(TLDAP, 'password', '')()
    

class UsersConfig(object):

    implements(ILDAPUsersConfig)
    adapts(ILDAPPlugin)
    
    def __init__(self, plugin):
        self.plugin = plugin

    baseDN = PropProxy(TUSERS, 'baseDN', '')()
    attrmap = PropProxy(TUSERS, 'attrmap', '{}', json=True)()
    scope = PropProxy(TUSERS, 'scope', '')()
    queryFilter = PropProxy(TUSERS, 'queryFilter', '')()
    objectClasses = PropProxy(TUSERS, 'objectClasses', '[]', json=True)()

    
class GroupsConfig(object):

    implements(ILDAPGroupsConfig)
    adapts(ILDAPPlugin)
    
    def __init__(self, plugin):
        self.plugin = plugin

    baseDN = PropProxy(TGROUPS, 'baseDN', '')()
    attrmap = PropProxy(TGROUPS, 'attrmap', '{}', json=True)()
    scope = PropProxy(TGROUPS, 'scope', '')()
    queryFilter = PropProxy(TGROUPS, 'queryFilter', '')()
    objectClasses = PropProxy(TGROUPS, 'objectClasses', '[]', json=True)()    