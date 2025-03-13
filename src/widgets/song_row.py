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
    _song_number = Gtk.Template.Child("song_number")
    _song_duration = Gtk.Template.Child("song_duration")

    queue_item = None

    def __init__(self):
        super().__init__()
        self._song_title.set_hexpand(True)


    def set_queue_item(self, queue_item):
        self.queue_item = queue_item
        self._song_title.set_markup(f"<span size=\"large\">{escape(queue_item.title)}</span>")
        if queue_item.track_number:
            self._song_number.set_markup(f"<span size=\"small\">{queue_item.track_number}</span>")
        self._song_duration.set_label(queue_item.duration_string())

