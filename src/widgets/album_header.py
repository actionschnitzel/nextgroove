# album_header.py
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

from gi.repository import GObject, Gtk, Gio
from .albumlistitem import AlbumListItem
from .song_row import SongRow
from html import escape



@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/albumheader.ui")
class AlbumHeader(Gtk.Box):

    __gtype_name__ = "AlbumHeader"

    _album_label = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()
    _album_year_label = Gtk.Template.Child()
    _songlist = Gtk.Template.Child("songlist")
    play_button = Gtk.Template.Child("play_button")

    _track_elements = Gio.ListStore()


    def __init__(self):
        super().__init__()
        self._album = None
        self._cover_image.set_size_request(128, 128)

        song_item_factory = Gtk.SignalListItemFactory()
        song_item_factory.connect("setup", self._setup_song_list_item)
        song_item_factory.connect("bind", self._bind_song_list_item)
        self._songlist.props.factory = song_item_factory
        song_selection_model = Gtk.SingleSelection.new(self._track_elements)
        self._songlist.props.model = song_selection_model
        self._songlist.connect("activate", self.song_clicked)

    def set_album(self, album):
        self.album = album
        self._album_label.set_markup(f"<span size=\"x-large\">{escape(album.album)}</span>")
        self._album_year_label.set_text(f"Released {album.year}")
        self.play_button.set_visible(True)

    def set_cover(self, cover_file):
        self._cover_image.set_from_file(cover_file)

    def set_tracks(self, tracks):
        self._track_elements.remove_all()
        # Add tracks
        for track in tracks:
            self._track_elements.append(track)

    def _setup_song_list_item(self, factory, list_item):
        list_item.props.child = SongRow()

    def _bind_song_list_item(self, factory, list_item):
        song_item = list_item.props.item
        song_row = list_item.props.child
        song_row.set_queue_item(song_item)

    def song_clicked(self, event, song_id):
        print(f"Clicked on song {song_id}")
