.. _settings:

.. py:currentmodule:: newauth.settings_dist

Settings
========

Settings in NewAuth works by subclassing :py:class:`BaseConfig` with "DevConfig" or "ProdConfig" or any other prefix.
The prefix will be read from `NEWAUTH_ENV` and default to "Dev".

.. autoclass:: BaseConfig

   .. autoattribute:: SECRET_KEY
       :annotation:
   .. autoattribute:: APP_DIR
       :annotation:
   .. autoattribute:: PROJECT_ROOT
       :annotation:
   .. autoattribute:: DEBUG
       :annotation:
   .. autoattribute:: SQLALCHEMY_DATABASE_URI
       :annotation:
   .. autoattribute:: SQLALCHEMY_ECHO
       :annotation:
   .. autoattribute:: EVE
       :annotation:
   .. autoattribute:: ADMIN_GROUP
       :annotation:
   .. autoattribute:: PING_GROUP
       :annotation:
   .. autoattribute:: PINGERS
       :annotation:
   .. autoattribute:: PINGERS_SETTINGS
       :annotation:
   .. autoattribute:: PLUGINS
       :annotation:

.. _mail_settings:

Mail Settings
-------------

::

    #: Mail settings for https://pythonhosted.org/flask-mail/
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_DEBUG = os.getenv('DEBUG', False)
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = None

.. _celery_settings:

Celery Settings
---------------

::

    #: Celery Settings, more available http://celery.readthedocs.org/en/latest/configuration.html
    CELERY_BROKER_URL = 'redis://localhost:6379'
    CELERY_RESULT_BACKEND = 'db+sqlite:///celery.sqlite'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'

.. _eve_settings:

Eve Settings
------------

The Eve settings configure your NewAuth instance with your corporation/alliance identity and needs. For NewAuth to work, it needs one or several corporation api keys that will allow it to query its contacts to compute a list of allowable characters. See :ref:`manage_update_contacts` for more informations. Here's an example for the `I Whip My Slaves Back and Forth` alliance::

    EVE = {
        'auth_name': 'J4LP',
        'requirements': {
            # Members need a mask of 65544538 and a key that does not expires
            # Allies need a mask of 50331656 and a key that can expires
            'internal': {'mask': 65544538, 'expires': False},
            'ally': {'mask': 50331656, 'expires': True}
        },
        'alliances': [99002172], # This is J4LP's alliance id
        'corporations': [],
        'keys': [(0, 'sekret')]
    }

The `alliances` and `corporations` lists are a list of entity ID to add by default when updating the contacts. Here's an example
