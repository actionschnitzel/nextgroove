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

import os.path
from html import escape

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio, GObject
from .albumtile import AlbumTile
from .queueitem import QueueItem
from .controls import Controls
from .artist import ArtistItem
from .album_header import AlbumHeader
from .albumlistitem import AlbumListItem
from .playlist_row import PlaylistRow
from .playlist_header import PlaylistHeader


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/window.ui")
class NextcloudmusicWindow(Adw.ApplicationWindow):
    """Main window"""

    __gtype_name__ = "NextcloudmusicWindow"

    # Widgets
    album_view = Gtk.Template.Child("albumview")
    artist_sidebar = Gtk.Template.Child("artist_sidebar")
    album_sidebar = Gtk.Template.Child("album_sidebar")
    album_details_content = Gtk.Template.Child("album_details_content")
    queue_view = Gtk.Template.Child("queueview")
    controls = Gtk.Template.Child("controls")
    album_click_menu = Gtk.Template.Child("album_click_menu")
    playlist_view = Gtk.Template.Child("playlistview")
    welcome_view = Gtk.Template.Child("welcomepage")

    #artist_nav_1 = Gtk.Template.Child("artist_nav_1")
    artist_nav_2 = Gtk.Template.Child("artist_nav_2")
    artist_nav_3 = Gtk.Template.Child("artist_nav_3")
    outer_artist_split = Gtk.Template.Child("outer_artist_split")
    #inner_artist_split = Gtk.Template.Child("inner_artist_split")
    album_navigation = Gtk.Template.Child("album_navigation")
    album_tab_details = Gtk.Template.Child("album_tab_details")
    album_tab_details_content = Gtk.Template.Child("album_tab_details_content")


    playlist_nav_view = Gtk.Template.Child()
    playlist_details_page = Gtk.Template.Child()
    playlistdetails = Gtk.Template.Child()

    stack = Gtk.Template.Child("stack")
    album_stack = Gtk.Template.Child("album_stack")
    playlist_stack = Gtk.Template.Child("playlist_stack")
    queue_stack = Gtk.Template.Child("queue_stack")
    artist_stack = Gtk.Template.Child("artist_stack")

    # Data objects
    _settings = None
    _client = None
    _media = None
    _queue = None
    _songs = None
    mpris = None

    _album_selected = None

    def __init__(self, **kwargs):
        """Standard constructor for the window, initialize things, and get the settings"""
        super().__init__(**kwargs)
        self._settings = Gio.Settings.new("net.rosebirch.nextgroove")
        self._queue = Gio.ListStore()
        self._songs = Gtk.ListStore(str, str, str, QueueItem)
        self._media = Gtk.MediaFile.new()
        self._artists = Gio.ListStore()
        self._selected_artist_content = Gio.ListStore()
        self._artist_albums = Gio.ListStore()

    def set_mpris(self, mpris):
        self.mpris = mpris
        self.controls.set_mpris(mpris)

    def set_client(self, client):
        """Connections created to link everything.
        Touches album view, queue view, media controls"""
        self._client = client
        print("Setting client")

        # We like Albums
        if not self.album_view.props.factory:
            album_item_factory = Gtk.SignalListItemFactory()
            album_item_factory.connect("setup", self._setup_list_item)
            album_item_factory.connect("bind", self._bind_list_item)
            self.album_view.props.factory = album_item_factory
        if not self.album_view.props.model:
            selection_model = Gtk.MultiSelection.new(client.albums)
            self.album_view.props.model = selection_model
            self.album_view.connect("activate", self.album_clicked)

        # TODO ok this is too much, split out each tab into a separate class

        # Queue page
        queue_item_factory = Gtk.SignalListItemFactory()
        queue_item_factory.connect("setup", self._setup_queue_list_item)
        queue_item_factory.connect("bind", self._bind_queue_list_item)
        self.queue_view.props.factory = queue_item_factory
        selection_model = Gtk.MultiSelection.new(self._queue)
        self.queue_view.props.model = selection_model
        self.queue_view.connect("activate", self.queue_clicked)

        # Artist Sidebar
        artist_sidebar_factory = Gtk.SignalListItemFactory()
        artist_sidebar_factory.connect("setup", self._setup_artist_sidebar_list_item)
        artist_sidebar_factory.connect("bind", self._bind_artist_sidebar_list_item)
        self.artist_sidebar.props.factory = artist_sidebar_factory
        selection_model = Gtk.MultiSelection.new(self._artists)
        self.artist_sidebar.props.model = selection_model
        self.artist_sidebar.connect("activate", self.artist_clicked)
        # Selected artist Album content
        album_sidebar_factory = Gtk.SignalListItemFactory()
        album_sidebar_factory.connect("setup", self._setup_album_sidebar_list_item)
        album_sidebar_factory.connect("bind", self._bind_album_sidebar_list_item)
        self.album_sidebar.props.factory = album_sidebar_factory
        selection_model = Gtk.MultiSelection.new(self._artist_albums)
        self.album_sidebar.props.model = selection_model
        self.album_sidebar.connect("activate", self.album_sidebar_clicked)
        # Artist Coontent
        self.album_details_content.play_button.connect("clicked", self.artist_album_play_clicked_artist_view)
        self.album_details_content.append_button.connect("clicked", self.artist_album_append_clicked_artist_view)
        self.album_details_content.append_next_button.connect("clicked", self.artist_album_append_next_clicked_artist_view)
        self.album_details_content.set_window(self)
        self.album_tab_details_content.play_button.connect("clicked", self.artist_album_play_clicked_album_view)
        self.album_tab_details_content.append_button.connect("clicked", self.artist_album_append_clicked_album_view)
        self.album_tab_details_content.append_next_button.connect("clicked", self.artist_album_append_next_clicked_album_view)
        self.album_tab_details_content.set_window(self)
        self.album_tab_details_content.set_album_view()

        # Playlist page
        playlist_item_factory = Gtk.SignalListItemFactory()
        playlist_item_factory.connect("setup", self._setup_playlist_list_item)
        playlist_item_factory.connect("bind", self._bind_playlist_list_item)
        self.playlist_view.props.factory = playlist_item_factory
        playlist_selection_model = Gtk.MultiSelection.new(client.playlists)
        self.playlist_view.props.model = playlist_selection_model
        self.playlist_view.connect("activate", self.playlist_clicked)
        self.playlistdetails.play_button.connect("clicked", self.playlist_play_clicked)
        self.playlistdetails.append_button.connect("clicked", self.playlist_append_clicked)
        self.playlistdetails.append_next_button.connect("clicked", self.playlist_append_next_clicked)

        # Controls (next, previous, play/pause, now playing etc)
        self.controls.connections(self._client, self._media, self._queue, self)

    @GObject.Property(type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        return self._settings

    def update_collection(self, source_object, result, user_data):
        """Updates the collection view.
        """
        collection = result.propagate_value().value

        # Hide welcome view
        self.welcome_view.props.visible = False
        self.album_stack.props.visible = True
        self.playlist_stack.props.visible = True
        self.queue_stack.props.visible = True
        self.artist_stack.props.visible = True
        self.stack.props.visible_child_name = "albums"
        if collection is None:
            print("Collection is none atm, come back later")
            return

        self._songs.clear()

        for artist in sorted(collection, key=self.get_artist_name):
            artist_string = artist["name"]
            artist_id = artist["id"]
            artist_list_item = ArtistItem(artist_string, artist_id)
            self._artists.append(artist_list_item)
            for album in sorted(artist["albums"], key=self.get_artist_name):
                album_string = album["name"]
                album_id = album["id"]
                for song in sorted(album["tracks"], key=self.get_track_number):
                    song_string = song["title"]
                    song_id = list(song["files"].values())[0]
                    song_item = QueueItem(song_string, song_id, album_id, artist_id)
                    self._songs.append([artist_string, album_string, song_string, song_item])
        print(f"we have {len(self._songs)} songs")

        print(f"We have {len(self._artists)} artists")

        # Trick the UI to redraw, no redraw call works
        # I am clearly doing something wrong here!
        fake_item = QueueItem("FAKE", -1, -1, -1)
        self._queue.insert(0, fake_item)
        self._queue.remove(0)

    def get_artist_name(self, thing):
        return thing['name'].lower()
    def get_track_number(self, thing):
        disk = thing.get('disk', 1) or 1
        number = thing.get('number', 1) or 1
        return f"{disk:02d}_{number:02d}"


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
        album_list_item.set_widget(album_widget)
        cover = self._client.get_cover(album_list_item)
        if cover and os.path.exists(cover):
            album_widget.set_cover(cover)
        else:
            self._client.download_cover_async(
                album_list_item.album_id, album_list_item.cover_url, album_widget
            )

    def album_clicked(self, event, album_id):
        self._album_selected = album_id
        album_tile = event.get_model()[album_id].widget
        popover = Gtk.PopoverMenu.new_from_model(self.album_click_menu)
        popover.set_parent(album_tile)
        popover.popup()

    def album_play_clicked(self, event, something):
        """Connected to activate signal from AlbumTile.
        A single click currently activates this and will attempt to play that album
        """
        album_index = self._album_selected
        album = self._client.albums[album_index]
        self.album_play_clicked_generic(album)

    def album_play_clicked_generic(self, album):
        album_id = album.album_id
        print(f"Clicked play on album '{album.album}' from artist {album.artist}")
        album_details = self._client.album_details(album)
        artist_id = self._client.get_artist_id_for_album_list_item(album)

        # Tracks are not ordered in the json output
        sorted_tracks = sorted(album_details["tracks"], key=lambda item: item["number"])

        # GOTCHA songs contain an ID and each file (for which I've only seen one) has an ID
        # we need that file ID, which makes this look quite ugly
        song_id = list(sorted_tracks[0]["files"].values())[0]
        song_name = sorted_tracks[0]["title"]
        self._queue.remove_all()
        for song in sorted_tracks:
            queued_song_id = list(song["files"].values())[0]
            song_item = QueueItem(song["title"], queued_song_id, album_id, artist_id)
            if queued_song_id == song_id:
                song_item.set_now_playing(True)
            self._queue.append(song_item)

        self._client.get_song_async(song_id, song_name, self.song_file_returned)


    def album_view_details_clicked(self, event, something):
        album_index = self._album_selected
        album = self._client.albums[album_index]
        album_id = album.album_id
        print(f"Clicked on album {album.album}")
        self.album_tab_details_content.set_album(album)

        self.album_tab_details_content.set_tracks(album.tracks)
        cover = self._client.get_cover(album)
        if cover and os.path.exists(cover):
            self.album_tab_details_content.set_cover(self._client.get_cover(album))
        else:
            self._client.download_cover_async(
                album.album_id, album.cover_url, self.album_tab_details_content
            )
        # FIXME actually probably want this as a page inside the album cover to make the nav work
        self.album_navigation.push(self.album_tab_details)

    def album_queue_add_end_clicked(self, event, something):
        album_index = self._album_selected
        album = self._client.albums[album_index]
        self.album_queue_add_end_clicked_generic(album)

    def album_queue_add_end_clicked_generic(self, album):
        if len(self._queue) == 0:
            print("Add to end of queue is identical to play when no queue: rerouting...")
            self.album_play_clicked_generic(album)
            return

        album_id = album.album_id
        print(f"Clicked add to end of queue on album '{album.album}' from artist {album.artist}")
        album_details = self._client.album_details(album)
        artist_id = self._client.get_artist_id_for_album_list_item(album)

        # Tracks are not ordered in the json output
        sorted_tracks = sorted(album_details["tracks"], key=lambda item: item["number"])

        # GOTCHA songs contain an ID and each file (for which I've only seen one) has an ID
        # we need that file ID, which makes this look quite ugly
        for song in sorted_tracks:
            queued_song_id = list(song["files"].values())[0]
            song_item = QueueItem(song["title"], queued_song_id, album_id, artist_id)
            self._queue.append(song_item)

    def album_queue_add_next_clicked(self, event, something):
        album_index = self._album_selected
        album = self._client.albums[album_index]
        self.album_queue_play_next_generic(album)

    def album_queue_play_next_generic(self, album):
        album_id = album.album_id
        if len(self._queue) == 0:
            print("Add to next in queue is identical to play when no queue: rerouting...")
            self.album_play_clicked_generic(album)
            return

        print(f"Clicked add to end of queue on album '{album.album}' from artist {album.artist}")
        album_details = self._client.album_details(album)
        artist_id = self._client.get_artist_id_for_album_list_item(album)

        # Tracks are not ordered in the json output
        sorted_tracks = sorted(album_details["tracks"], key=lambda item: item["number"])

        # GOTCHA songs contain an ID and each file (for which I've only seen one) has an ID
        # we need that file ID, which makes this look quite ugly
        insert_index = 0
        for queue_song in self._queue:
            if queue_song.is_now_playing():
                break
            insert_index += 1
        print(f"discovered now playing at queue position {insert_index}")
        for song in reversed(sorted_tracks):
            queued_song_id = list(song["files"].values())[0]
            song_item = QueueItem(song["title"], queued_song_id, album_id, artist_id)
            self._queue.insert(insert_index+1, song_item)


    ##################
    # Artist Sidebar #
    ##################

    def _setup_artist_sidebar_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Generate UI"""
        list_item.props.child = Gtk.Label()


    def _bind_artist_sidebar_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        artist_list_item = list_item.props.item
        artist_label = list_item.props.child
        artist_label.set_label(artist_list_item.artist)
        artist_label.set_halign(Gtk.Align.START)

    def artist_clicked(self, artist_list_id, list_number):
        artist = self._artists[list_number]
        print(f"Clicked on artist {artist.artist}")
        self._artist_albums.remove_all()
        artist_collection = self._client.artist_details(artist)
        for album in artist_collection['albums']:
            # TODO retrieve this? I'm sure I left one of these lying around somewhere
            album_list_item = AlbumListItem(
                    artist.artist, album['name'], album['cover'], album['id']
            )
            album_list_item.set_collection(album)
            self._artist_albums.append(album_list_item)
        #help(self.outer_artist_split)
        self.outer_artist_split.push(self.artist_nav_2)


    def _setup_album_sidebar_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Generate UI"""
        list_item.props.child = Gtk.Label()


    def _bind_album_sidebar_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        album_list_item = list_item.props.item
        album_label = list_item.props.child
        album_label.set_label(album_list_item.album)
        album_label.set_halign(Gtk.Align.START)

    def album_sidebar_clicked(self, artistalbum_list_id, list_number):
        print("clicked album sidebar")
        album = self._artist_albums[list_number]
        print(f"Clicked on album {album.album}")
        self.album_details_content.set_album(album)

        self.album_details_content.set_tracks(album.tracks)
        cover = self._client.get_cover(album)
        if cover and os.path.exists(cover):
            self.album_details_content.set_cover(self._client.get_cover(album))
        else:
            self._client.download_cover_async(
                album.album_id, album.cover_url, self.album_details_content
            )
        self.outer_artist_split.push(self.artist_nav_3)

    def artist_album_play_clicked_artist_view(self, _):
        album = self.album_details_content.album
        return self.artist_album_play_clicked(album)

    def artist_album_play_clicked_album_view(self, _):
        album = self.album_tab_details_content.album
        return self.artist_album_play_clicked(album)

    def artist_album_play_clicked(self, album):
        album_details = self._client.album_details(album)
        album_id = album_details['id']
        artist_id = self._client.get_artist_id_for_album_list_item(album)

        # Tracks are not ordered in the json output
        sorted_tracks = sorted(album_details["tracks"], key=lambda item: item["number"] or -1)

        # GOTCHA songs contain an ID and each file (for which I've only seen one) has an ID
        # we need that file ID, which makes this look quite ugly
        song_id = list(sorted_tracks[0]["files"].values())[0]
        song_name = sorted_tracks[0]["title"]
        self._queue.remove_all()
        for song in sorted_tracks:
            queued_song_id = list(song["files"].values())[0]
            song_item = QueueItem(song["title"], queued_song_id, album_id, artist_id)
            if queued_song_id == song_id:
                song_item.set_now_playing(True)
            self._queue.append(song_item)
        self._client.get_song_async(song_id, song_name, self.song_file_returned)

    def artist_album_append_clicked_artist_view(self, _):
        album = self.album_details_content.album
        self.album_queue_add_end_clicked_generic(album)

    def artist_album_append_clicked_album_view(self, _):
        album = self.album_tab_details_content.album
        self.album_queue_add_end_clicked_generic(album)

    def artist_album_append_next_clicked_artist_view(self, _):
        album = self.album_details_content.album
        self.album_queue_play_next_generic(album)

    def artist_album_append_next_clicked_album_view(self, _):
        album = self.album_tab_details_content.album
        self.album_queue_play_next_generic(album)


    ##############
    # Queue View #
    ##############

    def _setup_queue_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Generate UI element"""
        list_item.props.child = Gtk.Box()
        song_label = Gtk.Label()
        song_label.set_halign(1)
        song_label.set_hexpand(True)
        song_label.set_parent(list_item.props.child)
        albumartist_label = Gtk.Label()
        albumartist_label.set_halign(2)
        albumartist_label.set_parent(list_item.props.child)

    def _bind_queue_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Populate UI element.
        As we don't have a specialised widget, we just make the now playing the bold one.
        """
        queue_list_item = list_item.props.item
        if queue_list_item.artist_id == -1:
            # This is being called with a fake value to redraw the others, ignore this
            return

        song_widget = list_item.props.child.get_first_child()
        albumartist_widget = song_widget.get_next_sibling()

        if queue_list_item.album_id not in self._client.album_name_by_id:
            # We are repopulating during a client refresh, try again soon
            return
        album_str = self._client.album_name_by_id[queue_list_item.album_id]
        if queue_list_item.artist_id not in self._client.artist_name_by_id:
            # We are repopulating during a client refresh, try again in a sec
            return
        artist_str = self._client.artist_name_by_id[queue_list_item.artist_id]

        if queue_list_item.is_now_playing():
            song_widget.set_markup(f"<b>{queue_list_item.get_title()}</b>")
            albumartist_widget.set_markup(f"<b>{escape(artist_str)}  <i>{escape(album_str)}</i></b>")
        else:
            albumartist_widget.set_markup(f"{escape(artist_str)}  <i>{escape(album_str)}</i>")
            song_widget.set_text(queue_list_item.get_title())

    def queue_clicked(self, event, queue_id):
        """When (double) clicked on the queue item, play it!"""
        song = self._queue[queue_id]
        print(f"Clicked on song {song.get_title()} from queue")
        # Set other( or all until next section) songs in queue to not playing
        for _song in self._queue:
            _song.set_now_playing(False)
        # Set current song to playing to show in bold
        song.set_now_playing(True)

        self._client.get_song_async(song.get_song_id(), song.get_title(), self.song_file_returned)


    #################
    # Playlist view #
    #################

    def _setup_playlist_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Creates UI elements for album view"""
        list_item.props.child = PlaylistRow()

    def _bind_playlist_list_item(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        """Populates the UI elements for album view.
        Recalled if widget is updated, hence multiple branches depending on current stage
        """
        playlist_list_item = list_item.props.item
        playlist_widget = list_item.props.child
        playlist_widget.set_playlist(playlist_list_item)

    def playlist_clicked(self, event, playlist_id):
        playlist = self._client.playlists[playlist_id]
        playlist_name = playlist.playlist_name
        print(f"Clicked playlist {playlist_name}")
        track_ids = playlist.track_ids

        #self._queue.remove_all()

        #if len(track_ids)==0:
        #    print("empty playlist")
        #    return

        #for track in track_ids:
        #    queue_item = self._client.get_track_from_id(track)
        #    self._queue.append(queue_item)

        #first_song = self._queue[0]
        #first_song.set_now_playing(True)
        #self._client.get_song_async(first_song.song_id, first_song.title, self.song_file_returned)

        self.playlistdetails.set_playlist(playlist)
        self.playlistdetails.set_window(self)
        tracks = []
        for track in track_ids:
            tracks.append(self._client.get_track_from_id(track))
        self.playlistdetails.set_tracks(tracks)
        self._client.download_playlist_cover_async(playlist.playlist_id, playlist.cover, self.playlistdetails)
        self.playlist_nav_view.push(self.playlist_details_page)

    def playlist_play_clicked(self, event):
        playlist = self.playlistdetails.playlist
        playlist_name = playlist.playlist_name
        print(f"Clicked playlist {playlist_name}")
        track_ids = playlist.track_ids

        self._queue.remove_all()

        if len(track_ids)==0:
            print("empty playlist")
            return

        for track in track_ids:
            queue_item = self._client.get_track_from_id(track)
            self._queue.append(queue_item)

        first_song = self._queue[0]
        first_song.set_now_playing(True)
        self._client.get_song_async(first_song.song_id, first_song.title, self.song_file_returned)

    def playlist_append_clicked(self, event):
        playlist = self.playlistdetails.playlist
        playlist_name = playlist.playlist_name
        print(f"Clicked playlist {playlist_name}")
        track_ids = playlist.track_ids

        if len(self._queue) == 0:
            self.playlist_play_clicked(event)
            return

        if len(track_ids)==0:
            print("empty playlist")
            return

        for track in track_ids:
            queue_item = self._client.get_track_from_id(track)
            self._queue.append(queue_item)

    def playlist_append_next_clicked(self, event):
        playlist = self.playlistdetails.playlist
        playlist_name = playlist.playlist_name
        print(f"Clicked playlist {playlist_name}")
        track_ids = playlist.track_ids

        if len(self._queue) == 0:
            self.playlist_play_clicked(event)
            return

        if len(track_ids)==0:
            print("empty playlist")
            return

        insert_index = 0
        for queue_song in self._queue:
            if queue_song.is_now_playing():
                break
            insert_index += 1

        for track in reversed(track_ids):
            queue_item = self._client.get_track_from_id(track)
            self._queue.insert(insert_index+1, queue_item)

    def update_playlists(self, event, foo, bar):
        pass


    ################
    # Shared usage #
    ################

    def current_song(self):
        for song in self._queue:
            if song.is_now_playing():
                return song
        print("FAILED to get current song")

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
        # Get QueueItem from queue to get full details
        self.controls.set_now_playing(self.current_song())
        self.mpris.new_song()

        # Trick the UI to redraw, no redraw call works
        # I am clearly doing something wrong here!
        fake_item = QueueItem("FAKE", -1, -1, -1)
        self._queue.insert(0, fake_item)
        self._queue.remove(0)

    def song_file_returned(self, source_object, result, user_data):
        song_file = result.propagate_value().value
        self.play_song(song_file, self._client.song_title_last_callback)

