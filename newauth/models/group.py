from newauth.models import db
from newauth.models.enums import GroupType


class GroupMembership(db.Model):
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    is_applying = db.Column(db.Boolean, default=False)
    application_text = db.Column(db.Text, nullable=True)
    applied_on = db.Column(db.DateTime, nullable=True)
    accepted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    can_ping = db.Column(db.Boolean, default=False)
    joined_on = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', backref=db.backref('groups', lazy='dynamic'), foreign_keys=[user_id])
    group = db.relationship('Group', foreign_keys=[group_id])
    accepted_by = db.relationship('User', foreign_keys=[accepted_by_id])


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.Enum(
        *[element.value for key, element in GroupType.__members__.items()], name='GroupType'
    ), nullable=False, default='Public')
    public_members = db.Column(db.Boolean, default=True)
    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now())

    members = db.relationship('GroupMembership', lazy='dynamic')

    def get_type(self):
        return GroupType(self.type)

    def set_type(self, type):
        self.type = type.value
