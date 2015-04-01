from flask import flash, request, current_app, render_template, redirect, url_for
from flask.ext.classy import FlaskView, route
from flask.ext.login import current_user, login_required
from newauth.models import AuthContact
from newauth.models.enums import AuthContactType
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
        contacts = {
            '-10': {'corporations': [], 'alliances': []},
            '-5': {'corporations': [], 'alliances': []},
            '5': {'corporations': [], 'alliances': []},
            '10': {'corporations': [], 'alliances': []},
        }
        for contact in AuthContact.query.filter(AuthContact.standing != 0).all():
            if not hasattr(contacts, str(contact.standing)):
                # Not in our defaults above. 
                # TODO: seems like this should be normalizing instead of ignoring?
                continue
            if contact.get_type() == AuthContactType.alliance:
                contacts[str(contact.standing)]['alliances'].append(contact)
            else:
                contacts[str(contact.standing)]['corporations'].append(contact)
        return render_template('extra/standings.html', contacts=contacts)
