import os
from blinker import Namespace
from flask import Flask, redirect, url_for, session, request, flash, current_app
from flask.ext.login import login_url
from flask.ext.mail import Mail
from flask_wtf import CsrfProtect
from werkzeug.utils import import_string

newauth_signals = Namespace()
mail = Mail()


def create_app():
    app = Flask(__name__, static_folder='public')

    app.environment = os.getenv('NEWAUTH_ENV', 'Dev')

    if app.environment != 'Test':
        CsrfProtect(app)

    app.config.from_object('newauth.settings.{}Config'.format(app.environment))

    from newauth.models import db, migrate, Message, redis, login_manager, celery
    from newauth.models.enums import CharacterStatus, GroupType, APIKeyStatus, AuthContactType
    db.init_app(app)
    migrate.init_app(app, db)
    redis.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    celery.init_app(app)

    # Initialize NewAuth plugins
    app.loaded_plugins = {}
    app.loaded_pingers = {}
    app.admin_user_hooks = []
    app.dashboard_hooks = []
    app.navbar = {'admin': [], 'extra': []}

    for plugin in app.config['PLUGINS']:
        imported_plugin = import_string(plugin)()
        imported_plugin.init_app(app)
        app.loaded_plugins[plugin] = imported_plugin

    for pinger in app.config['PINGERS']:
        imported_pinger = import_string(pinger)()
        imported_pinger.init_app(app)
        app.loaded_pingers[pinger] = imported_pinger

    from newauth.blueprints import AccountView, RegisterView, GroupsView, PingsView, AdminView, ExtraView
    AccountView.register(app)
    RegisterView.register(app)
    GroupsView.register(app)
    PingsView.register(app)
    AdminView.register(app)
    ExtraView.register(app)

    from newauth.assets import assets_env
    assets_env.init_app(app)

    from newauth.utils import humanize, format_datetime, pluralize, markdown_filter
    app.jinja_env.filters['humanize'] = humanize
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['pluralize'] = pluralize
    app.jinja_env.filters['markdown'] = markdown_filter
    app.jinja_env.globals['GroupType'] = GroupType


    @app.route('/')
    def home():
        return redirect(url_for('AccountView:login'))

    @app.context_processor
    def inject_globals():
        return {
            'Message': Message,
            'CharacterStatus': CharacterStatus,
            'GroupType': GroupType,
            'APIKeyStatus': APIKeyStatus,
            'AuthContactType': AuthContactType,
            'hooks': {
                'admin_user_hooks': app.admin_user_hooks,
                'dashboard_hooks': app.dashboard_hooks
            },
            'navbar': app.navbar
        }

    @app.before_request
    def check_session():
        if session.get('ip') != request.remote_addr:
            session.clear()
            session['ip'] = request.remote_addr
            flash('Session expired, please login.')
            return redirect(login_url('AccountView:login', next_url=request.url))

    return app
