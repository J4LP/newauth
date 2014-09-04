import os
from blinker import Namespace
from flask import Flask, redirect, url_for
from flask_wtf import CsrfProtect

newauth_signals = Namespace()

def create_app():
    app = Flask(__name__, static_folder='public')

    app.environment = os.getenv('NEWAUTH_ENV', 'Dev')

    if app.environment != 'Test':
        CsrfProtect(app)

    app.config.from_object('newauth.settings.{}Config'.format(app.environment))

    from newauth.models import db, migrate, Message, redis, login_manager
    from newauth.models.enums import CharacterStatus, GroupType, APIKeyStatus
    db.init_app(app)
    migrate.init_app(app, db)
    redis.init_app(app)
    login_manager.init_app(app)

    from newauth.blueprints import AccountView, RegisterView, GroupsView, PingsView
    AccountView.register(app)
    RegisterView.register(app)
    GroupsView.register(app)
    PingsView.register(app)

    from newauth.assets import assets_env
    assets_env.init_app(app)

    from newauth.utils import humanize, format_datetime, pluralize, markdown_filter
    app.jinja_env.filters['humanize'] = humanize
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['pluralize'] = pluralize
    app.jinja_env.filters['markdown'] = markdown_filter
    app.jinja_env.globals['GroupType'] = GroupType

    # Initialize NewAuth plugins
    from newauth.plugins.sync.ldap import ldap_sync
    ldap_sync.init_app(app)

    @app.route('/')
    def home():
        return redirect(url_for('AccountView:login'))

    @app.context_processor
    def inject_globals():
        return {
            'Message': Message,
            'CharacterStatus': CharacterStatus,
            'GroupType': GroupType,
            'APIKeyStatus': APIKeyStatus
        }

    return app
