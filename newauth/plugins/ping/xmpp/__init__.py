from concurrent import futures
from flask import current_app
from flask.ext.login import current_user
from newauth.plugins.ping import Pinger
import sleekxmpp


class XMPPPinger(Pinger):
    """
    Jabber pinger. Make sure to configure your offline messages settings if you don't want your server to explode.

    You will need to install sleekxmpp and dnspython and modify your settings file.

    Configuration:

    ========= =============================================
    Key       Description
    ========= =============================================
    host      The ejabberd server host
    immutable Whether users can disable or not xmpp pings.
    username  Username of user allowed to announce
    password  Password of user allowed to announce
    ========= =============================================

    Example:

    ```
    PINGERS_SETTINGS = {
        'newauth.XMPPPinger': {
            'host': 'example.com',
            'user': 'admin',
            'password': 'admin',
            'user_id_key': 'user_id'
        }
    }
    ```
    """

    name = "newauth.XMPPPinger"

    display_name = "Jabber"

    def __init__(self, ping=None):
        self.ping = ping
        self.config = current_app.config['PINGERS_SETTINGS']['newauth.XMPPPinger']
        self.immutable = self.config.get('immutable', False)

    @property
    def description(self):
        return """Jabber is a real time chat communication server.

* Server: **{config[host]}**
* JabberID: {current_user.user_id}@{config[host]}
""".format(config=self.config, current_user=current_user)

    def send_ping(self):

        def do_ping(ping, config, users):
            self.AnnounceBot(config['user'] + '@' + config['host'], config['password'], config, ping, users)

        executor = futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(do_ping, self.ping, self.config, self.ping.users.all())
        executor.shutdown(wait=True)

    def enabled(self, user):
        return True

    class AnnounceBot(sleekxmpp.ClientXMPP):
        def __init__(self, jid, password, config, ping, users):
            self.ping = ping
            self.config = config
            self.users = users
            import logging
            logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
            sleekxmpp.ClientXMPP.__init__(self, jid, password)
            self.connect(reattempt=False)
            self.add_event_handler('session_start', self.send_ping)
            self.process()
            self.disconnect(wait=True)

        def send_ping(self, event):
            for user in self.users:
                self.send_message(mto=getattr(user, self.config['user_id_key']) + '@' + self.config['host'], mbody=self.ping.text, mtype='chat')
            self.disconnect(wait=True)
