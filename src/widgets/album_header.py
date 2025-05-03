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
    _artist_label = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()
    _album_year_label = Gtk.Template.Child()
    _songlist = Gtk.Template.Child("songlist")
    play_button = Gtk.Template.Child("play_button")
    song_click_menu = Gtk.Template.Child("song_click_menu")
    song_click_menu_album_view = Gtk.Template.Child("song_click_menu_album_view")
    append_button = Gtk.Template.Child("append_button")
    append_next_button = Gtk.Template.Child("append_next_button")



    def __init__(self):
        super().__init__()
        self._track_elements = Gio.ListStore()
        self._album = None
        self._cover_image.set_size_request(128, 128)
        self.clicked_song = None

        song_item_factory = Gtk.SignalListItemFactory()
        song_item_factory.connect("setup", self._setup_song_list_item)
        song_item_factory.connect("bind", self._bind_song_list_item)
        self._songlist.props.factory = song_item_factory
        song_selection_model = Gtk.SingleSelection.new(self._track_elements)
        self._songlist.props.model = song_selection_model
        self._songlist.connect("activate", self.song_clicked)
        self.menu = self.song_click_menu

    def set_window(self, window):
        self.window = window

    def set_album_view(self):
        self.menu = self.song_click_menu_album_view

    def set_album(self, album):
        self.album = album
        self._album_label.set_markup(f"<span size=\"xx-large\">{escape(album.album)}</span>")
        self._artist_label.set_markup(f"<span size=\"x-large\">{escape(album.artist)}</span>")
        self._album_year_label.set_text(f"Released {album.year}")

    def set_cover(self, cover_file):
        self._cover_image.set_from_file(cover_file)

    def set_tracks(self, tracks):
        self._track_elements.remove_all()
        current_song = self.window.current_song()
        # Add tracks
        for track in tracks:
            if current_song and track.song_id == current_song.song_id:
                track.set_now_playing(True)
            self._track_elements.append(track)

    def _setup_song_list_item(self, factory, list_item):
        list_item.props.child = SongRow()

    def _bind_song_list_item(self, factory, list_item):
        song_item = list_item.props.item
        song_row = list_item.props.child
        song_row.set_queue_item(song_item)
        song_item.set_widget(song_row)

    def song_clicked(self, event, song_id):
        song_thing = self._track_elements[song_id]
        popover = Gtk.PopoverMenu.new_from_model(self.menu)
        popover.set_parent(song_thing.widget)
        popover.popup()
        self.clicked_song = song_thing

    def song_play_clicked(self, event, _):
        print(f"Let's play {self.clicked_song.title}")
        self.window._queue.remove_all()
        self.clicked_song.set_now_playing(True)
        self.window._queue.append(self.clicked_song)

        self.window._client.get_song_async(self.clicked_song.get_song_id(), self.clicked_song.title, self.window.song_file_returned)
        self.window.controls.set_queue_pos(0)

    def song_queue_add_end_clicked(self, event, _):
        if len(self.window._queue) == 0:
            print("Same as play if the queue is empty, redirecting")
            self.song_play_clicked(None, None)
            return

        self.window._queue.append(self.clicked_song)

    def song_queue_add_next_clicked(self, event, _):
        if len(self.window._queue) == 0:
            print("Same as play if the queue is empty, redirecting")
            self.song_play_clicked(None, None)
            return

        insert_index = 0
        for queue_song in self.window._queue:
            if queue_song.is_now_playing():
                break
            insert_index += 1

        self.window._queue.insert(insert_index+1 , self.clicked_song)


