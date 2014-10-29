from urlparse import urlparse, urljoin
from flask import request, url_for, redirect
from flask_wtf import Form
from wtforms import IntegerField, StringField, PasswordField, ValidationError, SelectField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from newauth.models import User


def email_check():
    def _email(form, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("{} is already being used.".format(field.data))
    return _email

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target

class APIKeyForm(Form):
    key_id = IntegerField('Key ID', validators=[DataRequired(message="The Key ID must be an integer.")])
    vcode = StringField('vCode', validators=[DataRequired(), Length(min=64, max=64, message="Wrong vCode length, it must be 64 long.")])


class RegisterForm(Form):
    user_id = StringField('user_id', validators=[DataRequired()])
    email = StringField('email', validators=[DataRequired(), Email(), email_check()])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm')


class LoginForm(Form):
    next = HiddenField()
    user_id = StringField('user_id', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or ''

    def redirect(self, endpoint='index', **values):
        if is_safe_url(self.next.data):
            return redirect(self.next.data)
        target = get_redirect_target()
        return redirect(target or url_for(endpoint, **values))


class AccountUpdateForm(Form):
    user_id = StringField('User ID', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    main_character = SelectField('Main Character', coerce=int, validators=[DataRequired()])
    password = PasswordField('Cur. Password', validators=[])
    new_password = PasswordField('New Password', validators=[EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Confirm New')


class GroupCreateForm(Form):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    public_members = BooleanField('Public member list', default=True)
    type = SelectField('Type', validators=[DataRequired()])


class GroupEditForm(Form):
    description = TextAreaField('Description', validators=[DataRequired()])
    public_members = BooleanField('Public member list', default=True)
    type = SelectField('Type', validators=[DataRequired()])


class GroupApplicationForm(Form):
    application_text = TextAreaField('Application Text', validators=[DataRequired()])


class PingForm(Form):
    category = HiddenField('Category', validators=[DataRequired(message='You must select a category')])
    message = TextAreaField('Message', validators=[DataRequired()])
    internal = BooleanField('Internal', default=False)
    ally = BooleanField('Ally', default=False)
    recipients = StringField('Recipients')


class AccountAdminUpdateForm(Form):
    user_id = StringField('User ID', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    main_character = SelectField('Main Character', coerce=int, validators=[DataRequired()])
    new_password = PasswordField('New Password')


class AccountRecoverForm(Form):
    user_id = StringField('User ID', validators=[])
    email = StringField('Email', validators=[])


class AccountDoRecoveryForm(Form):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
