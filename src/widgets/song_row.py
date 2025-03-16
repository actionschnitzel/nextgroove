# song_row.py
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


from __future__ import annotations
from typing import Optional

from gi.repository import GObject, Gtk
from .albumlistitem import AlbumListItem
from html import escape



@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/songrow.ui")
class SongRow(Gtk.Box):

    __gtype_name__ = "SongRow"

    _song_title = Gtk.Template.Child("title_label")
    _artist_title = Gtk.Template.Child("artist_label")
    _song_number = Gtk.Template.Child("song_number")
    _song_duration = Gtk.Template.Child("song_duration")

    queue_item = None

    def __init__(self):
        super().__init__()
        self._song_title.set_hexpand(True)

    def show_artist(self):
        self._artist_title.set_visible(True)

    def set_window(self, window):
        self.window = window

    def set_queue_item(self, queue_item):
        weight = "normal"
        self.queue_item = queue_item
        if queue_item.is_now_playing():
            weight = "bold"
        self._song_title.set_markup(f"<span weight=\"{weight}\" size=\"large\">{escape(queue_item.title)}</span>")
        if queue_item.track_number and queue_item.track_number != -1:
            self._song_number.set_markup(f"<span weight=\"{weight}\" size=\"small\">{queue_item.track_number}</span>")
        if queue_item.duration and queue_item.duration != -1:
            self._song_duration.set_markup(f"<span weight=\"{weight}\">{queue_item.duration_string()}</span>")
        if self._artist_title.is_visible():
            self._song_number.set_label("")
            artist_label = self.window._client.artist_name_by_id[queue_item.artist_id]
            self._artist_title.set_markup(f"<span weight=\"{weight}\" size=\"small\">{escape(artist_label)}</span>")

