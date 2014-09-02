from flask.ext.login import LoginManager
from flask.ext.migrate import Migrate
from flask.ext.redis import Redis
from flask.ext.sqlalchemy import SQLAlchemy


db = SQLAlchemy()
migrate = Migrate()
redis = Redis()
login_manager = LoginManager()

from .user import User
from .message import Message
from .api_key import APIKey
from .character import Character
from .auth_contact import AuthContact
from .group import GroupMembership, Group, GroupInvite
login_manager.login_view = 'AccountView:login'

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return None
    user.anonymous = False
    user.authenticated = True
    return user

