from passlib.hash import bcrypt, ldap_salted_sha1
from flask import current_app, flash, abort
from flask.ext.login import current_user
from newauth.app import newauth_signals
from newauth.models import db
from newauth.models.enums import CharacterStatus, APIKeyStatus


class User(db.Model):
    """User model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    name = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    status = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)
    last_ip = db.Column(db.String, default='127.0.0.1')
    last_login_on = db.Column(db.DateTime, default=db.func.now())
    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now())
    main_character_id = db.Column(db.Integer, nullable=True)
    anonymous = True
    authenticated = False

    main_character = db.relationship('Character', primaryjoin='foreign(User.main_character_id) == Character.id', uselist=False, cascade='all,delete', lazy='joined')
    characters = db.relationship('Character', backref=db.backref('owner'), primaryjoin='User.id == Character.owner_id', cascade='all,delete', lazy='dynamic')
    api_keys = db.relationship('APIKey', backref=db.backref('owner'), primaryjoin='User.id == APIKey.owner_id', cascade = 'all,delete', lazy='dynamic')
    messages = db.relationship('Message', backref=db.backref('created_by', cascade="all,delete"), primaryjoin='User.id == Message.created_by_id', cascade='all,delete')

    password_updated = newauth_signals.signal('user-updated-password')

    def update_password(self, new_password):
        """Hash a new password to bcrypt.

        :param new_password: The new password
        :type new_password: str

        """
        self.password = bcrypt.encrypt(new_password)

    def check_password(self, password):
        """Check if given password checks out.
        If the password is in a LDAP format, it will convert it to
        bcrypt.

        :param password: The password to compare
        :type password: str
        :returns: bool -- If the password checks out or not

        """
        if self.password[0:6] == '{SSHA}':
            # This is an old LDAP password, let's validate it and upgrade
            if ldap_salted_sha1.verify(password, self.password):
                self.password = bcrypt.encrypt(password)
                db.session.add(self)
                db.session.commit()
                return True
            else:
                return False
        return bcrypt.verify(password, self.password)

    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return self.anonymous

    def get_id(self):
        return unicode(self.id)

    def get_status(self):
        return CharacterStatus(self.status)

    def set_status(self, status):
        self.status = status.value

    def update_status(self):
        """Loop around characters and keys to determinate best status.

        Ineligible < Ally < Internal

        :returns CharacterStatus -- The status that was computed

        """
        account_status = CharacterStatus.ineligible
        for api_key in self.api_keys.all():
            api_key.validate()
            if api_key.get_status() == APIKeyStatus.valid:
                # Key is valid, let's look over the characters
                for character in api_key.characters.all():
                    character_status = character.get_status()
                    if character_status == CharacterStatus.ineligible:
                        # Nope
                        continue
                    elif character_status == CharacterStatus.ally and account_status != CharacterStatus.internal:
                        account_status = CharacterStatus.ally
                    elif character_status == CharacterStatus.internal:
                        # No need to go further.
                        account_status = CharacterStatus.internal
                        break
            if account_status == CharacterStatus.internal:
                break
        self.set_status(account_status)
        db.session.add(self)
        db.session.commit()

    def update_keys(self):
        """Update all API Keys and Characters associated."""
        from newauth.models import Character
        updated_characters = set()
        for api_key in self.api_keys.all():
            api_key.update_api_key()
            api_key.get_characters()
            for character in api_key.characters:
                updated_characters.add(character.id)
            db.session.add(api_key)
        characters_to_delete = Character.query.filter(db.not_(Character.id.in_(list(updated_characters)))).all()
        for character in characters_to_delete:
            db.session.delete(character)
        if self.main_character_id in characters_to_delete:
            del self.main_character_id
        db.session.add(self)
        db.session.commit()

    def is_member_of(self, group):
        groups = [membership.group_id for membership in self.groups]
        return group.id in groups

    def is_admin_of(self, group):
        return True if group.members.filter_by(user_id=self.id, is_admin=True).first() else False

    def has_applied_to(self, group):
        membership = group.members.filter_by(user_id=self.id).first()
        if membership:
            return membership.is_applying
        return False

    def is_admin(self):
        from newauth.models import Group
        admin_group = Group.query.filter_by(name=current_app.config['ADMIN_GROUP']).first()
        if not admin_group:
            current_app.logger.warning('Could not find ADMIN_GROUP.')
            return False
        if not admin_group.members.filter_by(user_id=current_user.id, is_admin=True).first():
            return False
        return True

    def __repr__(self):
        return '<User %r>' % self.user_id
