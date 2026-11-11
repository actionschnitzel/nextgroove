# playlist_row.py
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
from html import escape



@Gtk.Template(resource_path="/io/github/actionschnitzel/actiongroovenc/gtk/playlistrow.ui")
class PlaylistRow(Gtk.Box):

    __gtype_name__ = "PlaylistRow"

    playlist_title = Gtk.Template.Child("playlist_title")
    playlist_number = Gtk.Template.Child("playlist_number")
    playlist_duration = Gtk.Template.Child("playlist_duration")


    def __init__(self):
        super().__init__()

    def set_playlist(self, playlist):
        self.playlist = playlist
        self.playlist_title.set_markup(f"<span size=\"large\">{escape(playlist.playlist_name)}</span>")
        num_tracks = len(playlist.track_ids)
        self.playlist_number.set_markup(f"<span size=\"small\">{num_tracks} songs</span>")
        # TODO length of the playlist in total time duration
