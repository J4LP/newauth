import logging
import sys
from flask.ext.assets import ManageAssets
from flask.ext.migrate import MigrateCommand
from flask.ext.script import Manager, Server
from newauth.app import create_app
from newauth.models import db, AuthContact, User, Group, GroupMembership
from newauth.models.enums import GroupType

app = create_app()

manager = Manager(app)
manager.add_command('assets', ManageAssets)
manager.add_command('db', MigrateCommand)


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



if __name__ == '__main__':
    manager.run()
