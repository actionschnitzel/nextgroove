# controls.py
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
from gi.repository import Gio, GObject
from html import escape
from .albumtile import AlbumTile
from .queueitem import QueueItem

@Gtk.Template(resource_path='/net/rosebirch/nextcloudmusic/controls.ui')
class Controls(Gtk.ActionBar):
    __gtype_name__ = 'Controls'

    play_pause_button = Gtk.Template.Child("playpause")
    previous_button = Gtk.Template.Child("previous")
    next_button = Gtk.Template.Child("next")
    now_playing_label = Gtk.Template.Child("nowplaying")

    def __init__(self):
        super().__init__()
        self.set_size_request(120,50)
