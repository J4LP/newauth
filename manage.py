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
from newauth.plugins.sync.ldap import ldap_sync, LDAPUser

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
def import_from_ldap():
    """
    This command will read all entries in a ldap directory and import its users,
    running the necessary API calls.
    If the provided API Key is not working, the user will not be imported.
    :return:
    """
    with app.app_context():
        app.debug = True
        ldap_users = []
        with ldap_sync.connection as c:
            result = c.search(app.config['SYNC_LDAP_MEMBERDN'], '(uid=*)', SEARCH_SCOPE_WHOLE_SUBTREE, attributes=['*'])
            if result:
                for user in c.response:
                    # Is user already in Db ?
                    password = user['attributes']['userPassword'][0]
                    ldap_user = LDAPUser.from_ldap(user)
                    user_db = User.query.filter_by(user_id=ldap_user.uid).first()
                    if user_db:
                        app.logger.debug('{} is already registered.'.format(ldap_user.uid))
                        continue
                    user_model = User(
                        user_id=ldap_user.uid,
                        email=ldap_user.email,
                        password=password,
                        name=ldap_user.characterName
                    )
                    api_key = APIKey(
                        key_id=ldap_user.keyID,
                        vcode=ldap_user.vCode
                    )
                    try:
                        api_key.update_api_key()
                        for character in api_key.get_characters():
                            user_model.characters.append(character)
                    except Exception as e:
                        app.logger.exception(e)

                    for character in user_model.characters:
                        if character.name == ldap_user.characterName:
                            user_model.main_character_id = character.id
                            break

                    user_model.api_keys.append(api_key)
                    db.session.add(user_model)
                    db.session.commit()
                    try:
                        user_model.update_keys()
                        user_model.update_status()
                    except Exception as e:
                        app.logger.exception(e)
                    db.session.add(user_model)
                    db.session.commit()
                    app.logger.debug('{} has been imported.'.format(ldap_user.uid))


if __name__ == '__main__':
    manager.run()
