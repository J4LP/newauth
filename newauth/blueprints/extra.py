from flask import flash, request, current_app, render_template, redirect, url_for
from flask.ext.classy import FlaskView, route
from flask.ext.login import current_user, login_required
from newauth.models import AuthContact
from newauth.tasks import update_contacts


class ExtraView(FlaskView):

    @route('/standings', methods=['GET', 'POST'])
    @login_required
    def standings(self):
        if request.method == 'POST' and current_user.is_admin():
            update_contacts.delay()
            return redirect(url_for('AdminView:standings', updated=True))
        if request.args.get('updated') and current_user.is_admin():
            flash('Contacts will be updated shortly.', 'success')
        contacts = AuthContact.query.all()
        return render_template('extra/standings.html', contacts=contacts)
