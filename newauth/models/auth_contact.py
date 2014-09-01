import datetime
from enum import Enum
from flask import current_app
from newauth.eveapi import EveAPIQuery
from newauth.models import db
from newauth.models.enums import AuthContactType


CHARACTER_TYPES = (1373, 1374, 1375, 1376, 1377, 1378, 1379, 1380, 1381, 1382, 1383, 1384, 1385, 1386)
CORPORATION_TYPES = (2,)
ALLIANCE_TYPES = (16159,)


class AuthContact(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    name = db.Column(db.String, nullable=False)
    short_name = db.Column(db.String, nullable=True)
    type = db.Column(db.Enum(
        *[element.value for key, element in AuthContactType.__members__.items()], name='AuthContactType'
    ))
    standing = db.Column(db.Integer, default=0)
    members = db.Column(db.Integer, default=0, nullable=False)
    members_in_auth = db.Column(db.Integer, default=0)
    internal = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=False)
    added_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now())

    @classmethod
    def get_or_create(cls, **kwargs):
        contact = AuthContact.query.filter_by(id=kwargs['id']).first()
        if not contact:
            return cls(**kwargs)
        else:
            for k, v in kwargs.iteritems():
                setattr(contact, k, v)
            return contact

    @staticmethod
    def update_contacts():
        contacts_updated = set()
        auth_contacts = AuthContact.query.all()
        alliance_list = EveAPIQuery(public=True).get('eve/AllianceList')
        # Adding itself
        for alliance_id in current_app.config['EVE']['alliances']:
            alliance = None
            for a in alliance_list.row:
                if a.allianceID == alliance_id:
                    alliance = a
            if not alliance:
                current_app.logger.warning('Could not find alliance #{}'.format(alliance_id))
                continue
            if alliance_id not in contacts_updated:
                contacts_updated.add(alliance_id)
                db.session.add(AuthContact.get_or_create(
                    id=alliance.allianceID,
                    name=alliance.name,
                    short_name=alliance.shortName,
                    type=AuthContactType.alliance.value,
                    members=alliance.memberCount,
                    internal=True,
                    enabled=True,
                    updated_on=datetime.datetime.utcnow()
                ))
            for corporation in alliance.memberCorporations.row:
                sheet = EveAPIQuery(public=True).get('corp/CorporationSheet', corporationID=corporation.corporationID)
                if sheet.corporationID not in contacts_updated:
                    contacts_updated.add(sheet.corporationID)
                    db.session.add(AuthContact.get_or_create(
                        id=sheet.corporationID,
                        name=sheet.corporationName,
                        short_name=sheet.ticker,
                        type=AuthContactType.corporation.value,
                        members=sheet.memberCount,
                        internal=True,
                        enabled=True,
                        updated_on=datetime.datetime.utcnow()
                    ))

        for corporation_id in current_app.config['EVE']['corporations']:
            sheet = EveAPIQuery(public=True).get('corp/CorporationSheet', corporationID=corporation_id)
            if sheet.corporationID not in contacts_updated:
                contacts_updated.add(sheet.corporationID)
                db.session.add(AuthContact.get_or_create(
                    id=sheet.corporationID,
                    name=sheet.corporationName,
                    short_name=sheet.ticker,
                    type=AuthContactType.corporation.value,
                    members=sheet.memberCount,
                    enabled=True,
                    updated_on=datetime.datetime.utcnow()
                ))

        for key in current_app.config['EVE']['keys']:
            contact_list = EveAPIQuery(key_id=key[0], vcode=key[1]).get('corp/ContactList')
            for contact in contact_list.corporateContactList.row + contact_list.allianceContactList.row:
                if contact.contactTypeID in CHARACTER_TYPES:
                    pass  # We don't really care about character contacts
                elif contact.contactTypeID in CORPORATION_TYPES:
                    contacts_updated.add(sheet.corporationID)
                    sheet = EveAPIQuery(public=True).get('corp/CorporationSheet', corporationID=contact.contactID)
                    if sheet.corporationID not in contacts_updated:
                        contacts_updated.add(sheet.corporationID)
                        db.session.add(AuthContact.get_or_create(
                            id=sheet.corporationID,
                            name=sheet.corporationName,
                            short_name=sheet.ticker,
                            type=AuthContactType.corporation.value,
                            members=sheet.memberCount,
                            enabled=False,
                            updated_on=datetime.datetime.utcnow()
                        ))
                elif contact.contactTypeID in ALLIANCE_TYPES:
                    alliance = None
                    for a in alliance_list.row:
                        if a.allianceID == alliance_id:
                            alliance = a
                    if not alliance:
                        current_app.logger.warning('Could not find alliance #{}'.format(contact.contactID))
                        continue
                    if alliance.allianceID not in contacts_updated:
                        contacts_updated.add(alliance.allianceID)
                        db.session.add(AuthContact.get_or_create(
                            id=alliance.allianceID,
                            name=alliance.name,
                            short_name=alliance.shortName,
                            type=AuthContactType.alliance.value,
                            members=alliance.memberCount,
                            enabled=False,
                            updated_on=datetime.datetime.utcnow()
                        ))
                else:
                    current_app.logger.warning('Could not determinate contact type for contact: {}'.format(contact))
        contacts_to_delete = AuthContact.query.filter(db.not_(AuthContact.id.in_(list(contacts_updated)))).all()
        current_app.logger.info("Updating {} contacts and deleting {} contacts".format(len(contacts_updated), len(contacts_to_delete)))
        db.session.commit()
