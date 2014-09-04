from flask import render_template, redirect, url_for, flash, current_app, request, session, abort, jsonify
from flask.ext.login import current_user, login_user, login_required
from flask.ext.classy import FlaskView, route
from flask.ext.sqlalchemy import Pagination
from newauth.models import User
from newauth.utils import flash_errors, is_admin


class AdminView(FlaskView):

    decorators = [login_required, is_admin]

    def users(self):
        page = int(request.args.get('page', 1))
        users = User.query.paginate(page)
        return render_template('admin/users.html', users=users)
