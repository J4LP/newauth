import datetime
from flask import current_app
from newauth.models import db
from newauth.models.enums import APIKeyType, APIKeyStatus


class APIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    key_id = db.Column(db.Integer, nullable=False)
    vcode = db.Column(db.String(length=64), nullable=False)
    mask = db.Column(db.Integer, nullable=False)
    type = db.Column(db.Enum(
        *[element.value for key, element in APIKeyType.__members__.items()], name='APIKeyType'
    ))
    status = db.Column(db.Enum(
        *[element.value for key, element in APIKeyStatus.__members__.items()], name='APIKeyStatus'
    ))
    disabled = db.Column(db.Boolean, default=False, nullable=False)
    expires_on = db.Column(db.DateTime, nullable=True)
    error_count = db.Column(db.Integer, default=0)
    last_error_on = db.Column(db.DateTime, nullable=True)
    created_on = db.Column(db.DateTime, default=db.func.now())

    characters = db.relationship('Character', backref=db.backref('api_key'), primaryjoin='APIKey.id == Character.api_key_id', lazy='dynamic')

    @property
    def expires(self):
        return isinstance(self.expires_on, datetime.datetime)

    def get_api(self):
        from newauth.eveapi import EveAPIQuery
        return EveAPIQuery(api_key=self)

    def update_api_key(self):
        try:
            api_info = self.get_api().get('account/APIKeyInfo')
        except Exception as e:
            current_app.logger.exception(e)
            raise e
        self.mask = api_info.accessMask
        if api_info.expires:
            self.expires_on = api_info.expires
        else:
            self.expires_on = None
        self.set_type(APIKeyType(api_info.type))

    def set_type(self, type):
        self.type = type.value

    def get_type(self):
        return APIKeyType(self.type)

    def set_status(self, status):
        self.status = status.value

    def get_status(self):
        try:
            return APIKeyStatus(self.status)
        except Exception:
            self.status = 'Invalid'
            db.session.add(self)
            db.session.commit()
            return 'Invalid'

    def get_characters(self):
        from newauth.models import Character
        api_info = self.get_api().get('account/APIKeyInfo')
        self.characters = [Character.get_or_create(
            id=c.characterID,
            name=c.characterName,
            corporation_id=c.corporationID,
            corporation_name=c.corporationName,
            alliance_id=c.allianceID,
            alliance_name=c.allianceName,
            owner=self.owner if self.owner else None
        ) for c in api_info.characters.row]
        return self.characters

    def validate(self, save=True):
        mask_name = None
        for name, requirement in current_app.config['EVE']['requirements'].iteritems():
            if self.mask >= requirement['mask']:
                mask_name = name
        if not mask_name:
            self.set_status(APIKeyStatus.invalid_mask)
        else:
            if self.expires != current_app.config['EVE']['requirements'][mask_name]['expires']:
                self.set_status(APIKeyStatus.invalid_expiration)
            else:
                self.set_status(APIKeyStatus.valid)
        if save:
            db.session.add(self)
            db.session.commit()

    def get_auth_type(self):
        for name, requirement in current_app.config['EVE']['requirements'].iteritems():
            if self.mask == requirement['mask']:
                return name
        return 'Unrecognized type'

