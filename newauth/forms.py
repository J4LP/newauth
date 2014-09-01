from flask_wtf import Form
from wtforms import IntegerField, StringField, PasswordField, ValidationError, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from newauth.models import User


def email_check():
    def _email(form, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("{} is already being used.".format(field.data))
    return _email


class APIKeyForm(Form):
    key_id = IntegerField('Key ID', validators=[DataRequired(message="The Key ID must be an integer.")])
    vcode = StringField('vCode', validators=[DataRequired(), Length(min=64, max=64, message="Wrong vCode length, it must be 64 long.")])


class RegisterForm(Form):
    user_id = StringField('user_id', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired(), Email(), email_check()])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm')


class LoginForm(Form):
    user_id = StringField('user_id', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class AccountUpdateForm(Form):
    user_id = StringField('User ID', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    main_character = SelectField('Main Character', coerce=int, validators=[DataRequired()])
    password = PasswordField('Current Password', validators=[])
    new_password = PasswordField('New Password', validators=[EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm New')


class GroupCreateForm(Form):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    public_members = BooleanField('Public member list', default=True, validators=[DataRequired()])
    type = SelectField('Type', validators=[DataRequired()])


class GroupEditForm(Form):
    description = TextAreaField('Description', validators=[DataRequired()])
    public_members = BooleanField('Public member list', default=True, validators=[DataRequired()])
    type = SelectField('Type', validators=[DataRequired()])


class GroupApplicationForm(Form):
    application_text = TextAreaField('Application Text', validators=[DataRequired()])
