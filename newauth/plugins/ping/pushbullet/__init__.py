import json
import uuid
from flask import current_app, flash, url_for, request, session, abort, redirect
from flask.ext.login import current_user
from flask_wtf import Form
from itsdangerous import URLSafeTimedSerializer
import requests
from wtforms import StringField, SelectMultipleField
from wtforms.validators import DataRequired
from newauth.models import db, PingerConfiguration, User, Ping, celery
from newauth.plugins.ping import Pinger


class PingerForm(Form):
    devices = SelectMultipleField('Devices', description='Hold Ctrl/Cmd to select multiple devices.', choices=[])


class PushbulletPinger(Pinger):
    """
    Pushbullet pinger.

    You will need to install the pushbullet.py library. After enabling the plugin you will need to migrate NewAuth.

    """
    name = "newauth.PushbulletPinger"

    display_name = "Pushbullet"

    description = "Adds [Pushbullet](https://www.pushbullet.com/) support to receive pings on your phone and other devices."

    def __init__(self, app=None):
        super(PushbulletPinger, self).__init__(app)

    def init_app(self, app):
        super(PushbulletPinger, self).init_app(app)
        app.add_url_rule('/pingers/pushbullet', 'pushbullet', self.pushbullet_authorize)

    def get_form(self, user_config):
        if user_config:
            user_config = user_config.get_config()
            form = PingerForm(data={
                'api_key': user_config.get('api_key'),
                'devices': [device['id'] for device in user_config.get('devices_enabled', [])]
            })
            form.devices.choices = [(device['id'], device['name']) for device in user_config.get('devices_available', [])]
        else:
            form = PingerForm()
        return form

    def send_ping(self, ping):
        for user in ping.users.filter(User.pingers_configuration.any(pinger=self.name)).with_entities(User.id).all():
            send_pushbullet_ping.delay(ping.id, user[0])

    def enabled(self, user):
        configuration = user.pingers_configuration.filter_by(pinger=self.name).first()
        return not(not configuration or not configuration.enabled)

    def enable(self, user, configuration):
        if configuration.get('access_token'):
            req = requests.get('https://api.pushbullet.com/v2/users/me', auth=(configuration['access_token'], ''))
            if req.status_code == 401:
                # Unauthorized, deleting token and reauthenticating
                del configuration['access_token']
            else:
                data = req.json()
                if 'iden' in data:
                    # All good, that token still works
                    return True
                # No identification data
                del configuration['access_token']
        redirect_url = url_for('pushbullet', _external=True, _scheme=current_app.config['HTTP_SCHEME'])
        signer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        state = signer.dumps(uuid.uuid4().hex)
        return {
            'action': 'redirect',
            'url': 'https://www.pushbullet.com/authorize?client_id={}&redirect_uri={}&response_type=code&scope=everything&state={}'.format(current_app.config['PINGERS_SETTINGS'][self.name]['client_id'], redirect_url, state)
        }

    def disable(self, user, configuration):
        del configuration['access_token']
        return configuration

    def save_configuration(self, user, configuration, form):
        try:
            req = requests.get('https://api.pushbullet.com/v2/devices', auth=(configuration['access_token'], ''))
            req.raise_for_status()
            devices = req.json()['devices']
        except Exception as e:
            current_app.logger.exception(e)
            flash('Could not enable Pushbullet Pinger: ' + str(e), 'danger')
            return False
        configuration['devices_available'] = [{
            'name': device['nickname'],
            'id': device['iden']
        } for device in devices if device.get('nickname', False)]
        configuration['devices_enabled'] = []
        for device in form.devices.data:
            for _device in configuration['devices_available']:
                if _device['id'] == device:
                    configuration['devices_enabled'].append(_device)
                    break
        return configuration

    def pushbullet_authorize(self):
        signer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            signer.loads(request.args.get('state'), max_age=30)
        except Exception:
            flash('Could not authenticate Pushbullet redirection.', 'danger')
            return redirect(url_for('PingsView:settings'))
        code = request.args.get('code')
        if not code:
            flash('No authentication code provided by Pushbullet', 'danger')
            return redirect(url_for('PingsView:settings'))
        req = requests.post('https://api.pushbullet.com/oauth2/token', data={
            'grant_type': 'authorization_code',
            'client_id': current_app.config['PINGERS_SETTINGS'][self.name]['client_id'],
            'client_secret': current_app.config['PINGERS_SETTINGS'][self.name]['client_secret'],
            'code': code
        })
        try:
            req.raise_for_status()
        except Exception as e:
            current_app.logger.exception(e)
            flash('Could not retrieve token from Pushbullet: {}'.format(str(e)), 'danger')
            return redirect(url_for('PingsView:settings'))
        data = req.json()
        configuration = PingerConfiguration.query.filter_by(user=current_user, pinger=self.name).first()
        if not configuration:
            flash('No configuration found for Pushbullet pinger.', 'danger')
        else:
            config = configuration.get_config()
            config['access_token'] = data['access_token']
            try:
                req = requests.get('https://api.pushbullet.com/v2/devices', auth=(config['access_token'], ''))
                req.raise_for_status()
                devices = req.json()['devices']
            except Exception as e:
                current_app.logger.exception(e)
                flash('Could not retrieve Pushbullet devices: {}'.format(str(e)), 'danger')
                return False
            config['devices_available'] = [{
                'name': device['nickname'],
                'id': device['iden']
            } for device in devices if device.get('pushable', False)]
            configuration.set_config(config)
            db.session.add(configuration)
            db.session.commit()
            flash('Pushbullet authentication successful.', 'success')
        return redirect(url_for('PingsView:settings'))


@celery.task
def send_pushbullet_ping(ping_id, user_id):
    ping = Ping.query.get(ping_id)
    if not ping:
        raise Exception('Ping not found.')
    configuration = PingerConfiguration.query.filter_by(user_id=user_id, pinger=PushbulletPinger.name).first()
    if not configuration or not configuration.enabled:
        raise Exception('Pushbullet pinger not enabled for this user.')
    config = configuration.get_config()
    access_token = config.get('access_token')
    if not access_token:
        raise Exception('No valid API Key found for Pushbullet.')
    devices_sent = 0
    link = url_for('PingsView:ping', ping_id=ping.id, _external=True, _scheme=current_app.config['HTTP_SCHEME'])
    for device in config.get('devices_enabled', []):
        req = requests.post('https://api.pushbullet.com/v2/pushes', auth=(access_token, ''), data=json.dumps({
            'device_iden': device['id'],
            'type': 'note',
            'title': '{} - Ping - {}'.format(current_app.config['EVE']['auth_name'], ping.category.name),
            'body': ping.text + '\n\n' + link + '\n',
        }), headers={'content-type': 'application/json'})
        req.raise_for_status()
        devices_sent += 1
    return 'Sent to {} devices'.format(devices_sent)


