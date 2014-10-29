import datetime
import os


class BaseConfig(object):
    """File based configuration object."""

    #: Secret key for securing cookies.
    #: Generate one with `openssl rand --base64 64`
    SECRET_KEY = ''

    #: Application absolute path
    APP_DIR = os.path.abspath(os.path.dirname(__file__))

    #: Project root
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))

    #: Turn on debug mode by environment
    DEBUG = os.getenv('DEBUG', True)

    #: Default SQLAlchemy database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///newauth_db.sqlite'

    #: Turn on debug mode for SQLAlchemy (prints out queries)
    SQLALCHEMY_ECHO = os.getenv('DEBUG', True)

    #: Eve related settings, see :ref:`eve_settings`.
    EVE = {
        'auth_name': 'Your alliance name',
        'requirements': {
            'internal': {'mask': 0, 'expires': False},
            'ally': {'mask': 0, 'expires': True}
        },
        'alliances': [],
        'corporations': [],
        'keys': [(0, '')]
    }

    #: The admin group
    ADMIN_GROUP = 'Admin'

    #: The ping group
    PING_GROUP = 'Ping'

    #: Array of pings to load and use
    PINGERS = []

    #: Runtime configuration for pingers
    PINGERS_SETTINGS = {}

    #: Plugins list
    PLUGINS = []

    #: Mail settings for https://pythonhosted.org/flask-mail/
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_DEBUG = os.getenv('DEBUG', False)
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = None

    #: Celery Settings, more available http://celery.readthedocs.org/en/latest/configuration.html
    CELERY_BROKER_URL = 'redis://localhost:6379'
    CELERY_RESULT_BACKEND = 'db+sqlite:///celery.sqlite'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'

    #: HTTP scheme (can be http, https, etc...)
    HTTP_SCHEME = 'http'

    #: Serve name used to generate external urls
    #: See "More on SERVER_NAME" http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values
    SERVER_NAME = 'newauth.local:5002'


class DevConfig(BaseConfig):
    SQLALCHEMY_ECHO = False
    DEBUG = True


class TestConfig(BaseConfig):
    SECRET_KEY = 'TEST'
    DEBUG = True
    WTF_CSRF_ENABLED = False
