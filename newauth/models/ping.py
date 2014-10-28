import json
from newauth.models import db


pings_users = db.Table(
    'pings_users',
    db.Column('ping_id', db.Integer, db.ForeignKey('ping.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

pings_authcontacts = db.Table(
    'pings_authcontacts',
    db.Column('ping_id', db.Integer, db.ForeignKey('ping.id'), primary_key=True),
    db.Column('auth_contact_id', db.Integer, db.ForeignKey('auth_contact.id'), primary_key=True)
)

pings_groups = db.Table(
    'pings_groups',
    db.Column('ping_id', db.Integer, db.ForeignKey('ping.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True)
)


class PingCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    icon = db.Column(db.String)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_on = db.Column(db.DateTime, default=db.func.now())

    created_by = db.relationship('User', foreign_keys=[created_by_id])


class Ping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    ping_category_id = db.Column(db.Integer, db.ForeignKey('ping_category.id'))
    scope = db.Column(db.String)
    recipients = db.Column(db.String)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_on = db.Column(db.DateTime, default=db.func.now())

    users = db.relationship('User', secondary=pings_users, backref=db.backref('pings_received', lazy='dynamic'), lazy='dynamic')
    groups = db.relationship('Group', secondary=pings_groups, backref=db.backref('pings_received', lazy='dynamic'))
    contacts = db.relationship('AuthContact', secondary=pings_authcontacts, backref=db.backref('pings_received', lazy='dynamic'))
    sender = db.relationship('User', backref='pings_sent', foreign_keys=[sender_id])
    category = db.relationship('PingCategory', backref='pings', foreign_keys=[ping_category_id])


class PingerConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pinger = db.Column(db.String, nullable=False)
    configuration = db.Column(db.Text, default=lambda: dict())
    enabled = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship('User', backref=db.backref('pingers_configuration', lazy='dynamic'), foreign_keys=[user_id])

    def get_config(self):
        try:
            return json.loads(self.configuration)
        except Exception:
            return {}

    def set_config(self, config):
        self.configuration= json.dumps(config)
