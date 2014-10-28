import json
from flask import current_app, flash, url_for
from flask_wtf import Form
import requests
from wtforms import StringField, SelectMultipleField
from wtforms.validators import DataRequired
from newauth.models import db, PingerConfiguration, User, Ping, celery
from newauth.plugins.ping import Pinger


class PingerForm(Form):
    api_key = StringField('API Key', description='Find it on your [Pushbullet\'s account settings](https://www.pushbullet.com/account).', validators=[DataRequired()])
    devices = SelectMultipleField('Devices', description='Hold Ctrl/Cmd to select multiple devices', choices=[])


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

    def get_form(self, user_config):
        print('hello')
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

    def enable(self, user, configuration, form):
        try:
            req = requests.get('https://api.pushbullet.com/v2/devices', auth=(form.api_key.data, ''))
            req.raise_for_status()
            devices = req.json()['devices']
        except Exception as e:
            current_app.logger.exception(e)
            flash('Could not enable Pushbullet Pinger: ' + str(e), 'danger')
            return False
        configuration['api_key'] = form.api_key.data
        configuration['devices_available'] = [{
            'name': device['nickname'],
            'id': device['iden']
        } for device in devices]
        configuration['devices_enabled'] = []
        for device in form.devices.data:
            for _device in configuration['devices_available']:
                if _device['id'] == device:
                    configuration['devices_enabled'].append(_device)
                    break
        return configuration


@celery.task
def send_pushbullet_ping(ping_id, user_id):
    ping = Ping.query.get(ping_id)
    if not ping:
        raise Exception('Ping not found.')
    configuration = PingerConfiguration.query.filter_by(user_id=user_id).first()
    if not configuration or not configuration.enabled:
        raise Exception('Pushbullet pinger not enabled for this user.')
    config = configuration.get_config()
    api_key = config.get('api_key')
    if not api_key:
        raise Exception('No valid API Key found for Pushbullet.')
    devices_sent = 0
    link = url_for('PingsView:ping', ping_id=ping.id)
    for device in config.get('devices_enabled', []):
        req = requests.post('https://api.pushbullet.com/v2/pushes', auth=(config['api_key'], ''), data=json.dumps({
            'device_iden': device['id'],
            'type': 'link',
            'title': '{} - Ping - {}'.format(current_app.config['EVE']['auth_name'], ping.category.name),
            'body': ping.text,
            'url': link
        }), headers={'content-type': 'application/json'})
        print(req.text)
        req.raise_for_status()
        devices_sent += 1
    return 'Sent to {} devices'.format(devices_sent)


