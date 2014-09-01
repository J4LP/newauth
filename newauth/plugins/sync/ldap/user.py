from ldap3 import MODIFY_ADD, MODIFY_DELETE, MODIFY_REPLACE
from flask import current_app
from slugify import slugify
from marrow.schema.declarative import nil, Container, Attribute
from marrow.schema.util import Attributes
from newauth.models import User, db

class ValidationError(Exception):
    pass


class Transform(Container):
    def __call__(self, value):
        return value

    def native(self, value):
        return value


class NaiveTransform(Transform):
    kind = Attribute(default=unicode)

    def __call__(self, value):
        return self.kind(value)

    def native(self, value):
        return self.kind(value)


class Field(Attribute):
    required = Attribute(default=False)
    transform = Attribute(default=Transform())
    choices = Attribute(default=None)

    def __init__(self, *args, **kw):
        super(Field, self).__init__(*args, **kw)

        # Fields that aren't required naturally default to None.
        if not self.required:
            try:
                self.default
            except AttributeError:
                self.default = None

    def __set__(self, obj, value):
        try:
            self.default
        except AttributeError:
            pass
        else:
            if value is self.default:
                del obj[self._key]
                return

        if self.required and value in (None, nil):
            raise ValidationError("Required fields can not be empty or omitted.")

        if self.choices and value not in self.choices:
            raise ValidationError("Value not in allowed range.")

        super(Field, self).__set__(obj, value)

    def __delete__(self, obj):
        if self.required:
            raise ValidationError()

        super(Field, self).__del__(obj)


class String(Field):
    transform = Attribute(default=NaiveTransform(unicode))


class Number(Field):
    transform = Attribute(default=NaiveTransform(int))


class List(Field):
    contains = String()


class LDAPDocument(Container):
    __fields__ = Attributes(Field)


class LDAPUser(LDAPDocument):
    objectClass = List()
    dn = String()
    uid = String()
    email = String()
    accountStatus = String()
    alliance = String()
    corporation = String()
    characterName = String()
    authGroup = List()
    keyID = Number()
    vCode = String()

    LIST_ATTRIBUTES = ('objectClass', 'authGroup',)
    INT_ATTRIBUTES = ('keyID',)

    def __init__(self):
        self._original_ldap_attributes = {}
        super(LDAPUser, self).__init__()
        self.authGroup = []

    @classmethod
    def from_sql(cls, model):
        user = cls()
        session = db.create_scoped_session()
        model = session.query(User).get(model.id)

        user.objectClass = ['top', 'account', 'simpleSecurityObject', 'xxPilot']
        user.uid = model.user_id
        user.email = model.email
        user.accountStatus = model.status if model.status else 'Ineligible'
        if model.main_character:
            user.characterName = model.main_character.name
            user.alliance = model.main_character.alliance_name
            user.corporation = model.main_character.corporation_name
        else:
            user.characterName = ''
            user.alliance = ''
            user.corporation = ''
        user.keyID = model.main_character.api_key.key_id
        user.vCode = model.main_character.api_key.vcode
        user.authGroup = [membership.group.name for membership in model.groups.filter_by(is_applying=False)]
        user.dn = 'uid={},{}'.format(model.user_id, current_app.config['SYNC_LDAP_MEMBERDN'])
        return user

    @classmethod
    def from_ldap(cls, resource):
        user = cls()
        user.dn = resource['dn']
        user._original_ldap_attributes['dn'] = resource['dn']
        for k, v in resource['attributes'].iteritems():
            if k in cls.__fields__.keys():
                if k in cls.LIST_ATTRIBUTES:
                    setattr(user, k, v)
                    user._original_ldap_attributes[k] = v
                else:
                    if k in cls.INT_ATTRIBUTES:
                        setattr(user, k, int(v[0]))
                        user._original_ldap_attributes[k] = int(v[0])
                    else:
                        setattr(user, k, v[0])
                        user._original_ldap_attributes[k] = v[0]
        return user

    def update_with_model(self, model):
        session = db.create_scoped_session()
        model = session.query(User).get(model.id)

        self.objectClass = ['top', 'account', 'simpleSecurityObject', 'xxPilot']
        self.uid = model.user_id
        self.email = model.email
        self.accountStatus = model.status if model.status else 'Ineligible'
        if model.main_character:
            self.characterName = model.main_character.name
            self.alliance = model.main_character.alliance_name
            self.corporation = model.main_character.corporation_name
        else:
            self.characterName = ''
            self.alliance = ''
            self.corporation = ''
        self.keyID = model.main_character.api_key.key_id
        self.vCode = model.main_character.api_key.vcode
        self.authGroup = [membership.group.name for membership in model.groups.filter_by(is_applying=False)]

    def changes(self):
        ldif_changes = {}
        for key in self.__fields__.iterkeys():
            if key == 'dn':
                continue
            value = getattr(self, key)
            if key not in self._original_ldap_attributes:
                if isinstance(value, list) and value:
                    ldif_changes[key] = (MODIFY_ADD, value)
                elif value:
                    ldif_changes[key] = (MODIFY_ADD, [value])
            elif key in self._original_ldap_attributes and self._original_ldap_attributes[key] != value:
                if isinstance(value, list):
                    ldif_changes[key] = (MODIFY_REPLACE, value)
                else:
                    ldif_changes[key] = (MODIFY_REPLACE, [value])
            elif key in self._original_ldap_attributes and not value:
                ldif_changes[key] = (MODIFY_DELETE, [self._original_ldap_attributes[key]])
        return ldif_changes

