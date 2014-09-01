from flask import current_app

class Sync(object):
    """
    Synchronizer class for implementing a user synchronizer.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('SYNC_LDAP_HOST', '127.0.0.1')
        app.config.setdefault('SYNC_LDAP_PORT', '389')
        app.config.setdefault('SYNC_LDAP_ADMIN_USER', 'cn=admin,dc=example,dc=com')
        app.config.setdefault('SYNC_LDAP_ADMIN_PASS', 'password')
        app.config.setdefault('SYNC_LDAP_BASEDN', 'dc=example,dc=com')
        app.config.setdefault('SYNC_LDAP_MEMBERDN', 'ou=People,dc=example,dc=com')

        app.logger.debug('LDAP Synchronizer has been initialized. Attempting connection.')

        try:
            self.try_connection()
        except Exception as e:
            app.logger.error('LDAP Synchronizer could not connect to the LDAP server.')
            app.logger.exception(e)

    def try_connection(self):
        raise Exception('YO')


