# window.py
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

@Gtk.Template(resource_path='/net/rosebirch/nextcloudmusic/window.ui')
class NextcloudmusicWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NextcloudmusicWindow'

    musiclist = Gtk.Template.Child("list")
    album_view = Gtk.Template.Child("albumview")
    _settings = None
    _client = None
    _media = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._settings = Gio.Settings.new('net.rosebirch.nextcloudmusic')



    def _setup_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = Gtk.Label()

    def _bind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        album_list_item = list_item.props.item
        album_widget = list_item.props.child
        album_widget.set_text(album_list_item.album)
        #album_widget.props.album = album_list_item

    def set_client(self, client):
        self._client = client
        print("Setting client")
        # We like Albums
        album_item_factory = Gtk.SignalListItemFactory()
        album_item_factory.connect("setup", self._setup_list_item)
        album_item_factory.connect("bind", self._bind_list_item)
        self.album_view.props.factory = album_item_factory
        selection_model = Gtk.MultiSelection.new(client.albums)
        self.album_view.props.model = selection_model
        print("Connected model")

    @GObject.Property(
        type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    def update_if_valid(self, source_object, result, user_data):
        connected = result.propagate_value().value
        if connected:
            print("Connected")
            self.label.set_text("Connection complete")
        else:
            print("Failed")
            self.label.set_text("Connection failed")

    def update_collection(self, source_object, result, user_data):
        collection = result.propagate_value().value
        for artist in collection:
            artist_string = artist['name']
            for album in artist['albums']:
                album_string = album['name']
                #self.add_album(artist, album)
                for song in album['tracks']:
                    song_string = song['title']
                    song_id = list(song['files'].values())[0]
                    self.add_song(artist_string, album_string, song_string, song_id)
            break

    def add_album(self, artist, album):
        model = self.album_view.get_model()
        if not model:
            list_item_factory = Gtk.SignalListItemFactory()
            print("model doesn't exist yet")



    def add_song(self, artist, album, song, song_id):
        testlabel = Gtk.Label()
        testlabel.set_markup(f"<a href=\"{song_id}\"><b>{escape(artist)}</b> <i>{escape(album)}</i> {escape(song)}</a>")
        testlabel.connect("activate-link", self.song_clicked)
        self.musiclist.insert(testlabel, 0)

    def song_clicked(self, event, song_id):
        print(f"song pressed {event}, and song ID {song_id}")
        # FIXME do some async goodness here, but need to know if this bit works or I'm outta here
        song_file = self._client.get_song(song_id)
        print(f"Got a file: {song_file}")
        self._media = Gtk.MediaFile.new_for_filename(song_file)
        self._media.play()
