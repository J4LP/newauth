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

    #: Eve related settings
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

    ADMIN_GROUP = 'Admin'


class DevConfig(BaseConfig):
    SQLALCHEMY_ECHO = False
    DEBUG = True


class TestConfig(BaseConfig):
    SECRET_KEY = 'TEST'
    DEBUG = True
    WTF_CSRF_ENABLED = False
