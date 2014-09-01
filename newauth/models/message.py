from newauth.models import db
from newauth.models.enums import MessageDisplay, MessageType



class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(
        *[element.value for key, element in MessageType.__members__.items()], name='MessageType'
    ), nullable=False)
    display_on = db.Column(db.Enum(
        *[element.value for key, element in MessageDisplay.__members__.items()], name='MessageDisplay'
    ), default=MessageDisplay.All.value, nullable=False)
    display_until = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_on = db.Column(db.DateTime(), default=db.func.now())

    @classmethod
    def display_for(cls, message_display):
        if not isinstance(message_display, MessageDisplay):
            message_display = MessageDisplay(message_display)
        return cls.query.filter_by(display_on=message_display.value)
