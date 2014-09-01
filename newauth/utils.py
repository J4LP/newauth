from functools import wraps
import arrow
from flask import flash, current_app, abort
from flask.ext.login import current_user
from newauth.models import Group


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), 'danger')


def humanize(date):
    try:
        return arrow.get(date).humanize()
    except Exception:
        return 'Invalid date'


def format_datetime(date):
    try:
        return arrow.get(date).format('DD MMMM YYYY - hh:ss')
    except Exception:
        return 'Invalid date'


def pluralize(str, number):
    if str[-1] != 's' and number != 1:
        return str + 's'
    return str


def is_admin(f):
    """
    Checks whether or not the current user belongs to the admin group
     defined in the settings
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
