.. _pings:

Pings
=====

A Ping is a message sent through NewAuth to a group of people registered. It can be sent over XMPP or Pushbullet for example.

.. _xmpp_pinger:

XMPP Pinger
-----------

NewAuth can send its pings to a Jabber server. To enable this pinger, add ``newauth.plugins.ping.xmpp.XMPPPinger`` to the `PINGERS` setting.

.. autoclass:: newauth.plugins.ping.xmpp.XMPPPinger


.. _pushbullet_pinger:

Pushbullet Pinger
-----------------

NewAuth can send its pings to `Pushbullet <https://pushbullet.com>`__, a notification web service that has applications for Chrome, Android, iOS and more.

To enable this pinger, add ``newauth.plugins.ping.pushbullet.PushbulletPinger`` to the `PINGERS` setting.


.. _pinger_model:

Create your own Pinger
----------------------

You would need to subclass and implement the :py:class:`newauth.plugins.ping.Pinger`.

.. autoclass:: newauth.plugins.ping.Pinger
    :members:
