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
from gi.repository import Gtk

@Gtk.Template(resource_path='/net/rosebirch/nextcloudmusic/settings.ui')
class NextcloudmusicSettingsWindow(Adw.PreferencesDialog):
    __gtype_name__ = 'NextcloudmusicSettingsWindow'

    _server_row = Gtk.Template.Child()
    _user_row = Gtk.Template.Child()
    _token_row = Gtk.Template.Child()

    _settings = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def present(self, window):
        self._settings = window.props.settings

        # Set previous values and connect to update them if needed
        self._server_row.connect("changed", self._update_server)
        self._server_row.set_text(self._settings.get_string("server"))
        self._user_row.connect("changed", self._update_user)
        self._user_row.set_text(self._settings.get_string("user"))
        self._token_row.connect("changed", self._update_token)
        self._token_row.set_text(self._settings.get_string("token"))
        super().present(window)

    def _update_server(self, server_row):
        self._settings.set_string("server", server_row.get_text())

    def _update_user(self, user_row):
        self._settings.set_string("user", user_row.get_text())

    def _update_token(self, token_row):
        self._settings.set_string("token", token_row.get_text())
