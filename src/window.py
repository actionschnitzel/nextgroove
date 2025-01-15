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


@Gtk.Template(resource_path="/net/rosebirch/nextcloudmusic/window.ui")
class NextcloudmusicWindow(Adw.ApplicationWindow):
    """Main window"""

    __gtype_name__ = "NextcloudmusicWindow"

    # Widgets
    collection_view = Gtk.Template.Child("collectionview")
    album_view = Gtk.Template.Child("albumview")
    queue_view = Gtk.Template.Child("queueview")
    controls = Gtk.Template.Child("controls")
    popover = Gtk.Template.Child("popover")
    album_play_button = Gtk.Template.Child("album_play_button")

    # Data objects
    _settings = None
    _client = None
    _media = None
    _queue = None
    _songs = None

    def __init__(self, **kwargs):
        """Standard constructor for the window, initialize things, and get the settings"""
        super().__init__(**kwargs)
        self._settings = Gio.Settings.new("net.rosebirch.nextcloudmusic")
        self._queue = Gio.ListStore()
        self._songs = Gtk.ListStore(str, str, str, QueueItem)
        self._media = Gtk.MediaFile.new()

        self.popover.props.position = Gtk.PositionType.LEFT

    def set_client(self, client):
        """Connections created to link everything.
        Touches album view, queue view, media controls"""
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
        self.album_play_button.connect("clicked", self.album_play_clicked)

        # Queue page
        queue_item_factory = Gtk.SignalListItemFactory()
        queue_item_factory.connect("setup", self._setup_queue_list_item)
        queue_item_factory.connect("bind", self._bind_queue_list_item)
        self.queue_view.props.factory = queue_item_factory
        selection_model = Gtk.MultiSelection.new(self._queue)
        self.queue_view.props.model = selection_model
        self.queue_view.connect("activate", self.queue_clicked)

        # Collection page
        self.collection_view.props.model = self._songs
        self.collection_view.connect("row-activated", self.collection_clicked)

        # Controls (next, previous, play/pause, now playing etc)
        self.controls.connections(self._client, self._media, self._queue, self)

    @GObject.Property(type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    ############################
    # Collection view (hidden) #
    ############################


    def collection_clicked(self, treeview, row, column):
        artist_name, album_name, song_title, queue_item = self._songs[row]
        song_file = self._client.get_song(queue_item.get_song_id())
        print(f"Got a file: {song_file} with id {queue_item.get_song_id()}")
        self.play_song(song_file, song_title)
        self._queue.remove_all()
        queue_item.set_now_playing(True)
        self._queue.append(queue_item)


    def update_collection(self, source_object, result, user_data):
        """Updates the collection view.
        This view is hidden by default as it is completely unfinished.
        This was before I realised how the model+view works in grid/list views.
        This ideally should be completely replaced with a song view using model+view style
        """
        collection = result.propagate_value().value
        for artist in sorted(collection, key=self.get_artist_name):
            artist_string = artist["name"]
            artist_id = artist["id"]
            for album in sorted(artist["albums"], key=self.get_artist_name):
                album_string = album["name"]
                album_id = album["id"]
                for song in sorted(album["tracks"], key=self.get_track_number):
                    song_string = song["title"]
                    song_id = list(song["files"].values())[0]
                    song_item = QueueItem(song_string, song_id, album_id, artist_id)
                    self._songs.append([artist_string, album_string, song_string, song_item])
                    #self.add_song(artist_string, album_string, song_string, song_id)
        print(f"we have {len(self._songs)} songs")

    def get_artist_name(self, thing):
        return thing['name']
    def get_track_number(self, thing):
        disk = thing.get('disk', 1)
        number = thing.get('number', 1)
        return f"{disk}_{number}"


    ##############
    # Album view #
    ##############

    def _setup_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Creates UI elements for album view"""
        list_item.props.child = AlbumTile()

    def _bind_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Populates the UI elements for album view.
        Recalled if widget is updated, hence multiple branches depending on current stage
        """
        album_list_item = list_item.props.item
        album_widget = list_item.props.child
        album_widget.set_album(album_list_item)
        if os.path.exists(self._client.get_cover(album_list_item)):
            album_widget.set_cover(self._client.get_cover(album_list_item))
        else:
            self._client.download_cover_async(
                album_list_item.album_id, album_list_item.cover_url, album_widget
            )

    def album_clicked(self, event, album_id):
        album = self._client.albums[album_id]
        print(f"Clicked album '{album.album}' from artist {album.artist}")
        # TODO make sure it appears near the album you clicked on.
        self.popover.popup()

    def album_play_clicked(self, event):
        """Connected to activate signal from AlbumTile.
        A single click currently activates this and will attempt to play that album
        """
        self.popover.popdown()
        album_id = self.album_view.get_model().get_selection().get_nth(0)
        print(f"got the slection as {album_id}")
        album = self._client.albums[album_id]
        print(f"Clicked play on album '{album.album}' from artist {album.artist}")
        album_details = self._client.album_details(album)
        artist_id = self._client.get_artist_id_for_album_list_item(album)

        # Tracks are not ordered in the json output
        sorted_tracks = sorted(album_details["tracks"], key=lambda item: item["number"])

        # GOTCHA songs contain an ID and each file (for which I've only seen one) has an ID
        # we need that file ID, which makes this look quite ugly
        song_id = list(sorted_tracks[0]["files"].values())[0]
        song_name = sorted_tracks[0]["title"]
        song_file = self._client.get_song(song_id)
        print(f"Got a file: {song_file} with id {song_id}")
        self.play_song(song_file, song_name)
        self._queue.remove_all()
        for song in sorted_tracks:
            queued_song_id = list(song["files"].values())[0]
            song_item = QueueItem(song["title"], queued_song_id, album_id, artist_id)
            if queued_song_id == song_id:
                song_item.set_now_playing(True)
            self._queue.append(song_item)

    ##############
    # Queue View #
    ##############

    def _setup_queue_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Generate UI element"""
        list_item.props.child = Gtk.Label()

    def _bind_queue_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Populate UI element.
        As we don't have a specialised widget, we just make the now playing the bold one.
        """
        queue_list_item = list_item.props.item
        queue_list_widget = list_item.props.child
        queue_list_item.set_widget(queue_list_widget)
        if queue_list_item.is_now_playing():
            queue_list_widget.set_markup(f"<b>{queue_list_item.get_title()}</b>")
        else:
            queue_list_widget.set_text(queue_list_item.get_title())

    def queue_clicked(self, event, queue_id):
        """When (double) clicked on the queue item, play it!"""
        song = self._queue[queue_id]
        print(f"Clicked on song {song.get_title()} from queue")
        song_file = self._client.get_song(song.get_song_id())
        # Set other( or all until next section) songs in queue to not playing
        for _song in self._queue:
            _song.set_now_playing(False)
        # Set current song to playing to show in bold
        song.set_now_playing(True)
        self.play_song(song_file, song.get_title())

    ################
    # Shared usage #
    ################

    def play_song(self, song_file, song_title):
        """Called from many places, even outside this class.
        song_file must already be downloaded so we can load it with mediafile.
        Then it needs to update any controls that need to know of current media etc
        Also has a hack to update the queue to force a redraw"""
        # I can't seem to reuse the same object, so make another
        # and then connect the damn signals again
        self._media = Gtk.MediaFile.new_for_filename(song_file)
        self._media.play()
        self.controls.connections(self._client, self._media, self._queue, self)
        self.controls.set_now_playing(song_title)

        # Trick the UI to redraw, no redraw call works
        # I am clearly doing something wrong here!
        fake_item = QueueItem("FAKE", 0, 0, 0)
        self._queue.insert(0, fake_item)
        self._queue.remove(0)
