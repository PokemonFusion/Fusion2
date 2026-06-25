"""PF2 channel command customizations."""

from evennia.commands.default.comms import CmdChannel as DefaultCmdChannel


class CmdChannel(DefaultCmdChannel):
    """Channel command that preserves the sending session for display identity."""

    def msg_channel(self, channel, message, **kwargs):
        kwargs.setdefault("sender_session", getattr(self, "session", None))
        super().msg_channel(channel, message, **kwargs)
