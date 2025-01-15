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
from .albumtile import AlbumTile
from .queueitem import QueueItem
from .controls import Controls
import os.path

@Gtk.Template(resource_path='/net/rosebirch/nextcloudmusic/window.ui')
class NextcloudmusicWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'NextcloudmusicWindow'

    musiclist = Gtk.Template.Child("list")
    album_view = Gtk.Template.Child("albumview")
    queue_view = Gtk.Template.Child("queueview")
    controls = Gtk.Template.Child("controls")
    _settings = None
    _client = None
    _media = None
    _queue = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._settings = Gio.Settings.new('net.rosebirch.nextcloudmusic')
        self._queue = Gio.ListStore()
        self._media = Gtk.MediaFile.new_for_filename("/tmp/doesnotexist")


    def _setup_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = AlbumTile()

    def _bind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        album_list_item = list_item.props.item
        album_widget = list_item.props.child
        album_widget.set_album(album_list_item)
        if os.path.exists(self._client.get_cover(album_list_item)):
            album_widget.set_cover(self._client.get_cover(album_list_item))
        else:
            self._client.download_cover_async(album_list_item.album_id, album_list_item.cover_url, album_widget)

    def _setup_queue_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = Gtk.Label()

    def _bind_queue_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        queue_list_item = list_item.props.item
        queue_list_widget = list_item.props.child
        queue_list_item.set_widget(queue_list_widget)
        if queue_list_item.is_now_playing():
            queue_list_widget.set_markup(f"<b>{queue_list_item.get_title()}</b>")
        else:
            queue_list_widget.set_text(queue_list_item.get_title())

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
        self.album_view.connect("activate", self.album_clicked)

        # Queue page
        queue_item_factory = Gtk.SignalListItemFactory()
        queue_item_factory.connect("setup", self._setup_queue_list_item)
        queue_item_factory.connect("bind", self._bind_queue_list_item)
        self.queue_view.props.factory = queue_item_factory
        selection_model = Gtk.MultiSelection.new(self._queue)
        self.queue_view.props.model = selection_model
        self.queue_view.connect("activate", self.queue_clicked)

        # Controls (next, previous, play/pause, now playing etc)
        self.controls.connections(self._client, self._media, self._queue, self)

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
        added = 0
        for artist in collection:
            artist_string = artist['name']
            for album in artist['albums']:
                album_string = album['name']
                #self.add_album(artist, album)
                for song in album['tracks']:
                    song_string = song['title']
                    song_id = list(song['files'].values())[0]
                    self.add_song(artist_string, album_string, song_string, song_id)
                    added += 1
                    if added >= 10:
                        break
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
        self.play_song(song_files, song_name="...")

    def album_clicked(self, event, album_id):
        album = self._client.albums[album_id]
        print(f"is your album {album.album}")
        album_details = self._client.album_details(album)

        sorted_tracks = sorted(album_details['tracks'], key=lambda item: item['number'])

        song_id = list(sorted_tracks[0]['files'].values())[0]
        song_name = sorted_tracks[0]['title']
        song_file = self._client.get_song(song_id)
        print(f"Got a file: {song_file} with id {song_id}")
        self.play_song(song_file, song_name)
        self._queue.remove_all()
        for song in sorted_tracks:
            # FIXME need to add more shit into the QueueItem so it can actually be played after
            queued_song_id = list(song['files'].values())[0]
            song_item = QueueItem(song['title'], queued_song_id)
            if queued_song_id == song_id:
                song_item.set_now_playing(True)
            self._queue.append(song_item)

    def queue_clicked(self, event, queue_id):
        print("clickerooni on the ol queue")

    def play_song(self, song_file, song_title):
        # I can't seem to reuse the same object, so make another
        # and then connect the damn signals again
        self._media = Gtk.MediaFile.new_for_filename(song_file)
        self._media.play()
        self.controls.connections(self._client, self._media, self._queue, self)
        self.controls.set_now_playing(song_title)

        # Trick the UI to redraw, no redraw call works
        # I am clearly doing something wrong here!
        fake_item = QueueItem('FAKE', 0)
        self._queue.insert(0, fake_item)
        self._queue.remove(0)

