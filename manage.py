import time
import logging
import sys
from ldap3 import SEARCH_SCOPE_WHOLE_SUBTREE
from flask import current_app
from flask.ext.assets import ManageAssets
from flask.ext.migrate import MigrateCommand
from flask.ext.script import Manager, Server
from newauth.app import create_app
from newauth.models import db, AuthContact, User, Group, GroupMembership, APIKey
from newauth.models.enums import GroupType
from newauth.plugins.sync.ldap import LDAPUser
from newauth.tasks import update_user

app = create_app()

manager = Manager(app)
manager.add_command('assets', ManageAssets)
manager.add_command('db', MigrateCommand)

for plugin in app.loaded_plugins.itervalues():
    if hasattr(plugin, 'ExtraCommands'):
        manager.add_command(plugin.ExtraCommands_prefix, plugin.ExtraCommands)

@manager.command
def update_contacts():
    with app.app_context():
        app.debug = True
        AuthContact.update_contacts()


@manager.command
def make_admin(user):
    with app.app_context():
        u = User.query.filter_by(user_id=user).first()
        if not u:
            raise Exception('Could not find user {}.'.format(user))
        g = Group.query.filter_by(name=app.config['ADMIN_GROUP']).first()
        if not g:
            g = Group(name=app.config['ADMIN_GROUP'], description='The admin group.', type=GroupType.hidden.value)
        membership = GroupMembership(user=u, is_admin=True, can_ping=True)
        g.members.append(membership)
        db.session.add(g)
        db.session.commit()


@manager.command
def make_ping(user):
    with app.app_context():
        u = User.query.filter_by(user_id=user).first()
        if not u:
            raise Exception('Could not find user {}.'.format(user))
        g = Group.query.filter_by(name=app.config['PING_GROUP']).first()
        if not g:
            g = Group(name=app.config['PING_GROUP'], description='The ping group.', type=GroupType.hidden.value)
        membership = GroupMembership(user=u, is_admin=True, can_ping=True)
        g.members.append(membership)
        db.session.add(g)
        db.session.commit()


@manager.command
def update_users(user_id=None):
    with app.app_context():
        if user_id:
            update_user.delay(user_id)
        else:
            user_ids = [a[0] for a in db.session.query(User.user_id).all()]
            for user_id in user_ids:
                update_user.delay(user_id)


if __name__ == '__main__':
    manager.run()
