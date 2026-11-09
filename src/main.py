# main.py
#
# Copyright 2024 Dean Birch
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import sys
import gi
from .client import NextcloudMusicClient
from .play_stats_dialog import PlayStatsDialog

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, GLib, Adw
from .window import NextcloudmusicWindow
from .settings import NextcloudmusicSettingsWindow
from .mpris import MPRIS
from .client import NextcloudMusicClient
from .nextcloud_login_dialog import NextcloudLoginDialog


class NextcloudmusicApplication(Adw.Application):
    """The main application singleton class."""

    _window = None
    _client = None

    def __init__(self):
        super().__init__(
            application_id="net.rosebirch.nextgroove",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action, ["<primary>p"])
        self.create_action("wrapped", self.on_wrapped_action)
        self.cookie = 0


    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = NextcloudmusicWindow(application=self)
            self.create_action("album_play_clicked", win.album_play_clicked)
            self.create_action("album_view_details_clicked", win.album_view_details_clicked)
            self.create_action("album_queue_add_end_clicked", win.album_queue_add_end_clicked)
            self.create_action("album_queue_add_next_clicked", win.album_queue_add_next_clicked)
            self.create_action("song_play_clicked", win.album_details_content.song_play_clicked)
            self.create_action("song_queue_add_end_clicked", win.album_details_content.song_queue_add_end_clicked)
            self.create_action("song_queue_add_next_clicked", win.album_details_content.song_queue_add_next_clicked)
            self.create_action("song_play_clicked_album_view", win.album_tab_details_content.song_play_clicked)
            self.create_action("song_queue_add_end_clicked_album_view", win.album_tab_details_content.song_queue_add_end_clicked)
            self.create_action("song_queue_add_next_clicked_album_view", win.album_tab_details_content.song_queue_add_next_clicked)
            self.create_action("song_play_clicked_playlist", win.playlistdetails.song_play_clicked)
            self.create_action("song_queue_add_end_clicked_playlist", win.playlistdetails.song_queue_add_end_clicked)
            self.create_action("song_queue_add_next_clicked_playlist", win.playlistdetails.song_queue_add_next_clicked)
            self.create_string_action("song_add_to_playlist_album", win.album_details_content.song_add_to_playlist_clicked)
            self.create_string_action("song_add_to_playlist_album_view", win.album_tab_details_content.song_add_to_playlist_clicked)
            self.create_string_action("song_add_to_playlist_playlist", win.playlistdetails.song_add_to_playlist_clicked)
            self.mpris = MPRIS(self)
            win.set_mpris(self.mpris)

        win.present()

        self._window = win
        self.update_client_credentials()

    def update_client_credentials(self):
        s = self._window.settings
        self._client = NextcloudMusicClient(self._window.settings)
        self._window.set_client(self._client)

        # If we've never logged in...
        if not self._client.initialized():
            self._window.welcome_description("Please login to a Nextcloud instance to use Nextgroove.")
            return

        callback = self._window.update_collection
        self._window.welcome_restart_spinner()
        self._client.collection_async(callback)
        playlist_callback = self._window.update_playlists
        self._client.playlist_async(playlist_callback)

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name="NextGroove",
            application_icon="net.rosebirch.nextgroove",
            comments="Linux client for Nextcloud Music",
            developer_name="Dean Birch",
            version="0.5.1",
            copyright="© Dean Birch\
            \
\n\nThis application comes with absolutely no warranty. See the GNU General Public Licence, version 3 or later for details.",
        )
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_("translator-credits"))
        about.set_issue_url("https://gitlab.gnome.org/dean36963/nextgroove/-/issues")
        about.present(self.props.active_window)


    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        settings = NextcloudmusicSettingsWindow()
        settings.present(self._window)

    def do_login(self, widget, _):
        dialog = NextcloudLoginDialog(0, self._window.settings, self._client)
        dialog.present(self._window)


    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def create_string_action(self, name, callback):
        """Add an application action taking a string parameter."""
        action = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
        action.connect("activate", callback)
        self.add_action(action)

    def quit(self):
        super().quit()
        # Update any changed settings
        self._window.settings.apply()

    def prevent_suspend(self):
        if self.cookie != 0:
            logging.debug("Already inhibiting suspend, returning")
            return

        self.cookie = self.inhibit(
            self._window,
            Gtk.ApplicationInhibitFlags.SUSPEND,
            "playing music"
        )
        if self.cookie != 0:
            logging.info("Successfully inhibited suspend.")
        else:
            logging.warning("FAILED to inhibit suspend")

    def allow_suspend(self):
        self.uninhibit(
            self.cookie
        )
        logging.info("Allowing suspend again")
        self.cookie = 0

    def on_wrapped_action(self, foo, bar):
        dialog = PlayStatsDialog(self._window.settings, self._client)
        dialog.present(self._window)


def main(version):
    """The application's entry point."""
    os.makedirs(NextcloudMusicClient.get_cache_dir(), exist_ok=True)
    logging.basicConfig(filename=os.path.join(NextcloudMusicClient.get_cache_dir(), "nextgroove.log"))
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(f"Logging under {NextcloudMusicClient.get_cache_dir()}")

    app = NextcloudmusicApplication()
    return app.run(sys.argv)
