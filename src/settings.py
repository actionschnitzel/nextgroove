# settings.py
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

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk

import logging
import os


@Gtk.Template(resource_path="/io/github/actionschnitzel/actiongroovenc/gtk/settings.ui")
class NextcloudmusicSettingsWindow(Adw.PreferencesDialog):
    __gtype_name__ = "NextcloudmusicSettingsWindow"

    _cache_row = Gtk.Template.Child()
    _clear_cache_row = Gtk.Template.Child()
    _login_row = Gtk.Template.Child()
    _logout_row = Gtk.Template.Child()
    _server_group = Gtk.Template.Child()

    _settings = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def present(self, window):
        self._settings = window.props.settings
        self.window = window

        if window.is_logged_in():
            self._login_row.props.visible = False
            self._logout_row.props.visible = True
            self._server_group.props.description = f"Logged into {window.props.settings.get_string("server")}"
        else:
            self._login_row.props.visible = True
            self._logout_row.props.visible = False
            server = window.props.settings.get_string("server")
            if server:
                self._server_group.props.description = f"Unable to login to {server}"
            else:
                self._server_group.props.description = f"Not logged into any server"

        # Set previous values and connect to update them if needed
        self._cache_row.connect("notify::active", self._update_use_cache)
        self._cache_row.set_active(self._settings.get_boolean("cache"))
        self._clear_cache_row.connect("activated", self._clear_cache)

        self._login_row.connect("activated", self._login_clicked)
        self._logout_row.connect("activated", self._logout_clicked)
        super().present(window)

    def _login_clicked(self, _):
        self.window._do_login(self)
        self.close()

    def _logout_clicked(self, _):
        title = "Disconnect Nextcloud?"
        body = "Do you want to sign out?"
        dialog = Adw.AlertDialog.new(title, body)
        dialog.add_response("close", "Cancel")
        dialog.add_response("disconnect", "Disconnect")
        dialog.set_response_appearance("disconnect", Adw.ResponseAppearance.DESTRUCTIVE)

        def handle_response(_o: Adw.AlertDialog, response: str) -> None:
            if response == "disconnect":
                self.window._do_logout()

        dialog.connect("response", handle_response)
        dialog.present(self)

    def _update_use_cache(self, cache_row, thing):
        logging.info(f"Now set cache to {cache_row.get_active()}")
        self._settings.set_boolean("cache", cache_row.get_active())

    def _clear_cache(self, cache_button):
        song_cache_dir = os.path.join(GLib.get_user_cache_dir(), "songs")
        logging.warning(f"About to clear cache under {song_cache_dir}")
        with os.scandir(song_cache_dir) as it:
            for entry in it:
                if entry.is_file():
                    logging.warn(f"Removing {entry.path}")
                    os.remove(entry.path)
