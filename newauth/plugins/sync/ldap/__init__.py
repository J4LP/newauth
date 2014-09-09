import random
import string
from ldap3 import Server, Connection, AUTH_SIMPLE, STRATEGY_SYNC, SEARCH_SCOPE_WHOLE_SUBTREE, MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE, LDAPException
from flask import current_app
from flask.ext.sqlalchemy import models_committed
from passlib.hash import ldap_salted_sha1
from slugify import slugify
from sqlalchemy.orm import make_transient
from newauth.models import User, Group, GroupMembership, db, APIKey
from newauth.plugins.sync.ldap.user import LDAPUser


class LDAPSync(object):
    """
    Synchronizer class implementing a LDAP Sync for pizza-auth
    """
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        app.config.setdefault('SYNC_LDAP_HOST', '127.0.0.1')
        app.config.setdefault('SYNC_LDAP_PORT', 389)
        app.config.setdefault('SYNC_LDAP_ADMIN_USER', 'cn=admin,dc=example,dc=com')
        app.config.setdefault('SYNC_LDAP_ADMIN_PASS', 'password')
        app.config.setdefault('SYNC_LDAP_BASEDN', 'dc=example,dc=com')
        app.config.setdefault('SYNC_LDAP_MEMBERDN', 'ou=People,dc=example,dc=com')

        app.logger.debug('LDAP Synchronizer has been initialized. Attempting connection.')

        try:
            self.setup_connection()
        except Exception as e:
            app.logger.error('LDAP Synchronizer could not connect to the LDAP server.')
            app.logger.exception(e)

        models_committed.connect_via(app)(self.handle_commit)
        User.new_user.connect_via(app)(self.insert_user)
        User.password_updated.connect_via(app)(self.update_user_password)

    def setup_connection(self):
        self.server = Server(self.app.config['SYNC_LDAP_HOST'], port=self.app.config['SYNC_LDAP_PORT'])
        self.connection = Connection(
            self.server,
            client_strategy=STRATEGY_SYNC,
            user=self.app.config['SYNC_LDAP_ADMIN_USER'],
            password=self.app.config['SYNC_LDAP_ADMIN_PASS'],
            authentication=AUTH_SIMPLE
        )

    def handle_commit(self, app, changes):
        """
        A handy signal in SQLAlchemy allows LDAPSync to be notified when a model has been modified.
        This function will separate the changes and dispatch them to the correct functions.
        """
        for model, change in changes:
            if isinstance(model, User):
                if change == 'update':
                    self.update_user(model)
            if isinstance(model, GroupMembership):
                self.update_membership(model)

    def get_uid(self, model):
        return '{},{}'.format(model.user_id, self.app.config['SYNC_LDAP_MEMBERDN'])

    def get_user(self, user_id):
        with self.connection as c:
            result = c.search(self.app.config['SYNC_LDAP_MEMBERDN'], '(uid={})'.format(user_id), SEARCH_SCOPE_WHOLE_SUBTREE, attributes=['*'])
            if result:
                if len(c.response) > 1:
                    raise Exception('Found more than one result for uid {}'.format(user_id))
                resource = c.response[0]
                return LDAPUser.from_ldap(resource)

    def save_user(self, ldap_user):
        changes = ldap_user.changes()
        if changes:
            with self.connection as c:
                c.modify(ldap_user.dn, changes)
                result = c.result

    def insert_user(self, app, model, password=None):
        with self.connection as c:
            result = c.search(self.app.config['SYNC_LDAP_MEMBERDN'], '(uid={})'.format(model.user_id), SEARCH_SCOPE_WHOLE_SUBTREE, attributes=['*'])
            if result:
                if len(c.response) != 0:
                    return self.update_user(model)
        ldap_user = LDAPUser.from_sql(model)
        attributes = {k: v for k, v in ldap_user.__dict__['__data__'].iteritems() if v is not None and k != 'dn' and k != 'objectClass' and v}
        if not password:
            attributes['userPassword'] = ldap_salted_sha1.encrypt(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(24)))
        else:
            attributes['userPassword'] = ldap_salted_sha1.encrypt(password)
        with self.connection as c:
            c.add(ldap_user.dn, object_class=['top', 'account', 'simpleSecurityObject', 'xxPilot'], attributes=attributes)
            result = c.result

    def update_user(self, model):
        ldap_user = self.get_user(model.user_id)
        if ldap_user:
            ldap_user.update_with_model(model)
            self.save_user(ldap_user)

    def update_membership(self, model):
        session = db.create_scoped_session()
        user = session.query(User).get(model.user_id)
        ldap_user = self.get_user(user.user_id)
        ldap_user.update_with_model(user)
        self.save_user(ldap_user)

    def delete_user(self, model):
        pass

    def update_user_password(self, app, model, password):
        ldap_user = self.get_user(model.user_id)
        with self.connection as c:
            c.modify(ldap_user.dn, {'userPassword': (MODIFY_REPLACE, [ldap_salted_sha1.encrypt(password)])})
            result = c.result

