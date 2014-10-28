import datetime
from flask import render_template, redirect, url_for, flash, current_app, request, session, abort, jsonify
from flask.ext.login import current_user, login_user, login_required
from flask.ext.classy import FlaskView, route
from werkzeug.utils import import_string
from newauth.forms import PingForm
from newauth.models import Group, AuthContact, Ping, PingCategory, User, Character, db, PingerConfiguration
from newauth.utils import flash_errors


class PingsView(FlaskView):

    decorators = [login_required]

    def history(self):
        pings = current_user.pings_received.order_by(db.desc(Ping.created_on)).all()
        return render_template('pings/history.html', pings=pings)

    @classmethod
    def register(cls, app, route_base=None, subdomain=None, route_prefix=None, trailing_slash=None):
        if hasattr(app, 'dashboard_hooks'):
            app.dashboard_hooks.append(cls._dashboard_hook)
        else:
            app.dashboard_hooks = [cls._dashboard_hook]
        return super(PingsView, cls).register(app, route_base, subdomain, route_prefix, trailing_slash)


    @route('new/', methods=['GET', 'POST'])
    def new(self):

        current_user_admin = current_user.is_admin()
        current_user_ping = bool(Group.query.filter_by(name=current_app.config['PING_GROUP']).first().members.filter_by(user_id=current_user.id, is_applying=False).first())

        categories = PingCategory.query.all()
        ping_form = PingForm()
        if ping_form.validate_on_submit():
            #ping_message.format(d=datetime.datetime.utcnow(), u=current_user.name)
            category = PingCategory.query.get(ping_form.category.data)
            if not category:
                flash("Category not found.", 'danger')
                return redirect(url_for('PingsView:new'))

            scopes = []
            if ping_form.internal.data:
                scopes.append('Internal')
            if ping_form.ally.data:
                scopes.append('Ally')

            if scopes and (not current_user_admin and not current_user_ping):
                flash("You are not allowed to Ping to this scope.", 'danger')
                return redirect(url_for('PingsView:new'))

            scopes_users = set()
            for scope in scopes:
                scopes_users |= set(User.query.filter_by(status=scope).all())

            groups = []
            contacts = []
            for recipient in ping_form.recipients.data.split(','):
                if 'group_' in recipient:
                    group = Group.query.get(recipient.split('group_')[1])
                    if group:
                        groups.append(group)
                    else:
                        flash("Could not find group #{}".format(recipient))
                        return redirect(url_for('PingsView:new'))
                elif 'contact_' in recipient:
                    contact = AuthContact.query.get(recipient.split('contact_')[1])
                    if contact:
                        contacts.append(contact)
                    else:
                        flash("Could not find contact #{}".format(recipient))
                        return redirect(url_for('PingsView:new'))

            groups_users = set()
            for group in groups:
                if current_user.can_ping_group(group) or current_user_admin or current_user_ping:
                    groups_users |= set(membership.user for membership in group.members.all())
                else:
                    flash("You are not allowed to ping to group '{}'".format(group.name))
                    return redirect(url_for('PingsView:new'))

            contacts_users = set()
            for contact in contacts:
                if current_user_admin or current_user_ping:
                    characters = Character.query.filter((Character.corporation_id==contact.id) | (Character.alliance_id==contact.id)).all()
                    contacts_users |= set(character.owner for character in characters)
                else:
                    flash("You are not allowed to ping to contact '{}'".format(contact.name))
                    return redirect(url_for('PingsView:new'))

            if scopes_users:
                if contacts_users:
                    if groups_users:
                        ping_users = scopes_users & contacts_users & groups_users
                    else:
                        ping_users = scopes_users & contacts_users
                else:
                    ping_users = scopes_users
            else:
                if contacts_users:
                    if groups_users:
                        ping_users = contacts_users & groups_users
                    else:
                        ping_users = contacts_users
                else:
                    if groups_users:
                        ping_users = groups_users
                    else:
                        flash("Empty results. Nobody would receive this ping.", 'danger')
                        return redirect(url_for('PingsView:new'))

            ping_message = ping_form.message.data.replace('{', '(').replace('}', ')') + '\n' + '== broadcast at {d} (UTC/EVE) from {u} to {r} =='
            recipients = ', '.join(scopes + [group.name for group in groups] + [contact.name for contact in contacts])
            ping = Ping(
                text=ping_message.format(d=datetime.datetime.utcnow(), u=current_user.name, r=recipients),
                scope=', '.join(scopes),
                recipients=recipients,
                users=list(ping_users),
                groups=list(groups),
                contacts=list(contacts),
                sender=current_user,
                category=category,
            )
            db.session.add(ping)
            db.session.commit()
            for pinger in current_app.loaded_pingers.itervalues():
                pinger.send_ping(ping)
            flash('Ping sent to {} members'.format(len(ping_users)))
            return redirect(url_for('PingsView:history'))
        flash_errors(ping_form)
        return render_template('pings/new.html', categories=categories)

    def search_recipients(self):
        name = request.args.get('name')
        if not name or len(name) < 3:
            abort(400)
        contacts = [{
            'id': 'contact_' + str(c[0]),
            'name': c[1],
            'type': c.type
        } for c in AuthContact.query.with_entities(AuthContact.id, AuthContact.name, AuthContact.type).filter(AuthContact.name.ilike('%' + name + '%')).all()[:10]]
        groups = [{
            'id': 'group_' + str(g[0]),
            'name': g[1],
            'type': 'group'
        } for g in Group.query.with_entities(Group.id, Group.name).filter(Group.name.ilike('%' + name + '%')).all()[:10]]
        return jsonify(results=groups + contacts)


    def settings(self):
        configurations = {
            config.pinger: config
            for config in PingerConfiguration.query.filter_by(user=current_user).all()
        }
        return render_template('pings/settings.html', configurations=configurations, pingers=current_app.loaded_pingers)

    @route('/settings/<pinger_name>', methods=['POST'])
    def save_settings(self, pinger_name):
        pinger = next((pinger for pinger in current_app.loaded_pingers.itervalues() if pinger.name == pinger_name), None)
        if not pinger:
            flash('Pinger not found or not enabled.', 'danger')
            return redirect(url_for('PingsView:settings'))
        configuration = PingerConfiguration.query.filter_by(user=current_user, pinger=pinger.name).first()
        if not configuration:
            configuration = PingerConfiguration(user=current_user, pinger=pinger.name)
        form = pinger.get_form(configuration)
        if not form.validate_on_submit():
            flash('Error saving pinger {}'.format(pinger.name), 'danger')
            flash_errors(pinger.instanced_form)
            return redirect(url_for('PingsView:settings'))
        config = pinger.enable(current_user, configuration.get_config(), form)
        if config is False:
            return redirect(url_for('PingsView:settings'))
        configuration.set_config(config)
        configuration.enabled = True
        db.session.add(configuration)
        db.session.commit()
        flash('Pinger {} enabled.'.format(pinger.name))
        return redirect(url_for('PingsView:settings'))

    @route('/history/<int:ping_id>')
    def ping(self, ping_id):
        ping = current_user.pings_received.filter_by(id=ping_id).first()
        if not ping:
            abort(404)
        return render_template('pings/ping.html', ping=ping)


    @staticmethod
    def _dashboard_hook(self):
        pings = current_user.pings_received.order_by(db.desc(Ping.created_on)).all()[:10]
        return render_template('pings/dashboard_hook.html', pings=pings)
