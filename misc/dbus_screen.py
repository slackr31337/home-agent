#!/usr/bin/env python3
# pylint: skip-file
# -*- coding: utf-8 -*-

from dbus.mainloop.glib import DBusGMainLoop

from gi.repository import GLib

import dbus
import logging
import sys


class ScreenSaverEventListener(object):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mainloop = DBusGMainLoop()
        self.loop = GLib.MainLoop()
        self.session_bus = dbus.SessionBus(mainloop=self.mainloop)

        self.receiver_args, self.receiver_kwargs = None, None

    def setup(self):
        self.receiver_args = (self.on_session_activity_change,)
        self.receiver_kwargs = dict(
            dbus_interface="org.freedesktop.login1",
            path="/org/freedesktop/login1/session",
            signal_name="PropertiesChanged",
            # callback arguments
            sender_keyword="sender",
            destination_keyword="dest",
            interface_keyword="interface",
            member_keyword="member",
            path_keyword="path",
            message_keyword="message",
        )

        self.session_bus.add_signal_receiver(
            *self.receiver_args, **self.receiver_kwargs
        )

    def on_session_activity_change(
        self, target: dbus.String, changed_properties: dbus.Dictionary, *args, **kwargs
    ):
        if (
            target != "org.gnome.SessionManager"
            or "SessionIsActive" not in changed_properties
        ):
            return

        if changed_properties.get("SessionIsActive"):
            self.on_session_unlock()
        else:
            self.on_session_lock()

    def on_session_lock(self):
        self.logger.info("Session Locked")

    def on_session_unlock(self):
        self.logger.info("Session Unlocked")

    def run(self):
        self.logger.debug("Starting event loop.")
        self.loop.run()

    def shutdown(self):
        self.logger.debug("Stopping event loop.")
        self.session_bus.remove_signal_receiver(
            *self.receiver_args, **self.receiver_kwargs
        )
        self.loop.quit()


def main():
    setup_logging()

    listener = ScreenSaverEventListener()
    listener.setup()

    try:
        listener.run()
    except KeyboardInterrupt:
        sys.stderr.write("ctrl+c received, shutting down...\n")
        listener.shutdown()


def setup_logging():
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    logging.addLevelName(logging.WARNING, "WARN")
    logging.getLogger().addHandler(console)
    logging.getLogger().setLevel(logging.DEBUG)


if __name__ == "__main__":
    main()
