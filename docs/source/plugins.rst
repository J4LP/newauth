.. _plugins:

Plugins
=======

NewAuth allows the loading of foreign plugins to extend its features. These plugins are loaded at the end of the creation of the application after models, routes and other settings have been loaded.

Plugins follow the architecture of a `Flask extension`_.

.. _Flask extension: http://flask.pocoo.org/docs/0.10/extensiondev/

.. _example_plugin:

Example plugin
--------------

This is an example of a NewAuth plugin that hooks into different signals and add a route to the admin.

.. code-block:: python

    class ExamplePlugin(object):
        """Example plugin for NewAuth"""

        def __init__(self, app=None):
            if app:
                self.init_app(app)

        def init_app(self, app):
            self.app = app

            self.app.logger.debug("ExamplePlugin enabled.")

            # Registering events
            User.login_success.connect_via(app)(self.login_success)
            User.login_fail.connect_via(app)(self.login_fail)

            # Registering template hooks
            if not hasattr(app, 'admin_user_hooks'):
                app.admin_user_hooks = [self.admin_user_hook]
            else:
                app.admin_user_hooks.append(self.admin_user_hook)
            if not hasattr(app, 'dashboard_hooks'):
                app.dashboard_hooks = [self.dashboard_hook]
            else:
                app.dashboard_hooks.append(self.dashboard_hook)

            # Registering routes
            app.add_url_rule('/admin/example', 'example_route', self.admin_example_route)

            # Registering to navbar
            app.navbar['admin'].append(('fa-info', 'Example Route', '/admin/example'))

        def login_success(self, app, user):
            current_app.logging.debug('Login success')

        def login_fail(self, app, user):
            current_app.logging.debug('Login fail')

        def admin_user_hook(self, user):
            return 'This will be displayed on the user\'s admin profile'

        def dashboard_hook(self, user):
            return 'This is a dashboard widget'

        def admin_example_route(self):
            return 'This is an extra route'



.. _ldap_plugin:

LDAP Plugin
-----------

NewAuth ships with a LDAP plugin that allow the application to save its user data to a LDAP directory.

Configuration
^^^^^^^^^^^^^

.. code-block:: python

    SYNC_LDAP_HOST = '127.0.0.1'
    SYNC_LDAP_ADMIN_USER = 'cn=admin,dc=example,dc=org'
    SYNC_LDAP_ADMIN_PASS = 'admin'
    SYNC_LDAP_BASEDN = 'dc=example,dc=org'
    SYNC_LDAP_MEMBERDN = 'ou=People,dc=example,dc=org'


Management commands
^^^^^^^^^^^^^^^^^^^

::

    python manage.py ldap import_users [--user_id $USER_ID]

This command will import all users in `SYNC_LDAP_MEMBERDN`. We recommend making a backup of your LDAP server before though. If you include add `--user_id` it will only import this user.


.. _tasks_dashboard:

Tasks Dashboard
---------------

NewAuth is using Celery to leverage some heavy tasks to the background, by default, no dashboard is available because it requires an external dependency. If you so wish, you can get a basic dashboard available to your admin and a better more functional one for your IT team. More information about Flower can be found `here`_.

Requirements
^^^^^^^^^^^^

This plugin requires you to install Flower, a Celery dashboard providing a REST API.

::

    pip install flower

We also need to run Flower alongside NewAuth and Celery with::

    celery -A newauth.tasks flower --address=127.0.0.1 --port=5555

Configuration
^^^^^^^^^^^^^

To enable `Tasks Dashboard`, add ``newauth.plugins.tasks_dashboard.TasksDasboard`` to the `PLUGINS` setting.

This plugin only requires one setting::

    CELERY_FLOWER_URL = 'http://127.0.0.1:5555/  # Note the trailing slash

.. _here: http://flower.readthedocs.org/en/latest/index.html

.. _pushbullet_pings:

Pushbullet pings
----------------

NewAuth can send its pings to `Pushbullet`_, a notification web service that has applications for Chrome, Android, iOS and more.

Requirements
^^^^^^^^^^^^

No requirements are needed for this plugin.


Configuration
^^^^^^^^^^^^^

To enable this pinger, add ``newauth.plugins.ping.pushbullet.PushbulletPinger`` to the `PLUGINS` setting.

.. _Pushbullet: https://pushbullet.com
