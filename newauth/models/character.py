from enum import Enum
from newauth.eveapi import EveAPIQuery
from newauth.models import db
from newauth.models.enums import CharacterStatus


class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    name = db.Column(db.String, nullable=False)
    corporation_id = db.Column(db.Integer, nullable=False)
    corporation_name = db.Column(db.String, nullable=False)
    alliance_id = db.Column(db.Integer, nullable=True)
    alliance_name = db.Column(db.String, nullable=True)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_key.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_on = db.Column(db.DateTime, default=db.func.now())
    last_updated_on = db.Column(db.DateTime, default=db.func.now())

    @classmethod
    def get_or_create(cls, **kwargs):
        character = Character.query.filter_by(id=kwargs['id']).first()
        if not character:
            return cls(**kwargs)
        else:
            for k, v in kwargs.iteritems():
                setattr(character, k, v)
            return character

    def get_status(self):
        from newauth.models.auth_contact import AuthContact
        corporation_contact = AuthContact.query.filter_by(id=self.corporation_id).first()
        if corporation_contact and corporation_contact.enabled:
            if corporation_contact.internal:
                return CharacterStatus.internal
            return CharacterStatus.ally
        elif not corporation_contact:
            alliance_contact = AuthContact.query.filter_by(id=self.alliance_id).first()
            if alliance_contact and alliance_contact.enabled:
                if alliance_contact.internal:
                    return CharacterStatus.internal
                return CharacterStatus.ally
        return CharacterStatus.ineligible

    def get_sheet(self):
        sheet = EveAPIQuery(api_key=self.api_key)
