from flask_wtf import Form


class Pinger(object):
    """
    Pinger base class to create a new pinger. Works like a plugin.
    """

    name = ""
    """Pinger name used for configuration storage and in other various places."""

    display_name = ""
    """Pinger name to be displayed."""

    description = ""
    """Description to be displayed, supports Markdown."""

    immutable = False
    """Can this pinger be disabled ?"""

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Called when the application starts, use to check for settings or register signals
        :param app:
        :return:
        """
        pass

    def get_form(self, user_config):
        """
        Return a WTForm to display on the pinger settings page or None if no configuration needed.
        :param user_config:
        :return:
        """
        raise NotImplementedError()

    def send_ping(self, ping):
        """
        Send the ping to the users.
        """
        raise NotImplementedError()

    def enabled(self, user):
        """
        Test if the user has the pinger enabled and configured.

        :rtype: boolean
        """
        raise NotImplementedError()

    def enable(self, user, configuration, form):
        """
        Called when enabling the pinger after the form has been validated.

        Feel free to flash messages through Flask's flash.

        `configuration` will be serialized, saved and tied to the user.

        :return: Return the configuration if successful or False
        """
        raise NotImplementedError()

    def disable(self, user, form):
        """
        Called when disabling the pinger.

        You can do additional steps before NewAuth disable this pinger for the user.

        Feel free to flash messages through Flask's flash.

        `configuration` will be serialized, saved and tied to the user.

        :return: Return the configuration if successful or False
        """
        raise NotImplementedError()

