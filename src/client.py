# client.py
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

import requests
import json
import os
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from gi.repository import GObject, Gio, GLib
from .albumlistitem import AlbumListItem
from functools import cmp_to_key
from .playlist import PlaylistItem
from .queueitem import QueueItem


class NextcloudMusicClient(GObject.Object):

    _auth = None
    _base_url = None
    collection = None
    albums = None
    albums_before_sorting = None
    _server = None
    _album_urls_by_id = None
    artist_name_by_id = None
    album_name_by_id = None
    song_title_last_callback = None
    playlists = None

    def __init__(self, server, user, token):
        super().__init__()
        self._base_url = f"{server}/index.php/apps/music/api"
        self._auth = HTTPBasicAuth(user, token)
        self.albums = Gio.ListStore()
        self.albums_before_sorting = Gio.ListStore()
        self._server = server
        self._album_urls_by_id = {}
        self.artist_name_by_id = {}
        self.album_name_by_id = {}
        self.playlists = Gio.ListStore()
        self.playlist_save_buffer = []

    def _collection(self):
        return requests.get(f"{self._base_url}/collection", auth=self._auth)

    def _playlists(self):
        return requests.get(f"{self._base_url}/playlists", auth=self._auth)

    def album_details(self, album_list_item):
        if not self.collection:
            # Happens during a client refresh, but then is called again once
            # everything is reinitialized
            return
        for artist in self.collection:
            if artist["name"] == album_list_item.artist:
                for album in artist["albums"]:
                    if album["name"] == album_list_item.album:
                        return album
        print("ERROR client.album_details could not find an album")
        return None

    def get_album_cover_url_from_song_id(self, song_id):
        for artist in self.collection:
            for album in artist['albums']:
                for song in album['tracks']:
                    if song['id'] == song_id:
                        cover = album['cover']
                        album_id = album['id']
                        return cover, album_id

    def artist_details(self, desired_artist):
        for artist in self.collection:
            if artist['id'] == desired_artist.artist_id:
                return artist

    def get_track_from_id(self, song_id):
        for artist in self.collection:
            for album in artist['albums']:
                for song in album['tracks']:
                    if song['id'] == song_id:
                        # We have a match
                        song_id = list(song['files'].values())[0]
                        queue_item = QueueItem(song['title'], song_id, album['id'], artist['id'])
                        queue_item.set_duration(song['length'])
                        queue_item.set_track_id(song["id"])
                        return queue_item
        print(f"get_track_from_id: Could not find track_id {song_id}")
        return None

    def get_artist_id_for_album_list_item(self, album_list_item):
        for artist in self.collection:
            if artist["name"] == album_list_item.artist:
                return artist["id"]
        print("ERROR client.get_artist_id_for_album_list_item could not find artist")
        return None

    def update_collection(self):
        # Clear existing collections
        self.albums.remove_all()
        self.albums_before_sorting.remove_all()
        self._album_urls_by_id = {}
        self.artist_name_by_id = {}
        self.album_name_by_id = {}
        self.playlists.remove_all()
        try:
            response = self._collection()
            if response.status_code != 200:
                print(f"return code was {response.status_code}")
                # Send errors back for toast on welcome page
                return f"Error: got HTTP status code {response.status_code} when checking collection"
            self.collection = json.loads(response.text)
            self.update_albums()
            return self.collection
        except requests.exceptions.RequestException as e:
            # Send errors back for toast on welcome page
            print(f"Exception in updating collection {e}")
            return f"Error: Got exception {e}"

    def update_albums(self):
        for artist in self.collection:
            artist_string = artist["name"]
            artist_id = artist["id"]
            self.artist_name_by_id[artist_id] = artist_string
            for album in artist["albums"]:
                album_string = album["name"]
                album_cover = album["cover"]
                album_id = album["id"]
                self.album_name_by_id[album_id] = album_string
                if album["cover"]:
                    self._album_urls_by_id[album["id"]] = album["cover"]
                else:
                    self._album_urls_by_id[album["id"]] = None
                album_item = AlbumListItem(
                    artist_string, album_string, album_cover, album_id
                )
                album_item.set_collection(album)
                self.albums_before_sorting.append(album_item)

        print(f"Retrieved albums and we have {len(self.albums_before_sorting)} albums")
        for album in sorted(
            self.albums_before_sorting,
            key=cmp_to_key(
                lambda album1, album2: self.latest_song_id_in_album(album1)
                - self.latest_song_id_in_album(album2)
            ),
            reverse=True,
        ):
            self.albums.append(album)
        print(f"Sorted albums and we have {len(self.albums)} albums")
        self.albums_before_sorting = None

    def latest_song_id_in_album(self, album_list_item):
        """Take the AlbumListItem object, retreives details,
        tracks can contain multiple, but find the largest id within there
        """
        album_object = self.album_details(album_list_item)
        latest_id = None
        for track in album_object["tracks"]:
            # Edge case for it not being set yet
            if not latest_id:
                latest_id = track["id"]
                continue

            if track["id"] > latest_id:
                latest_id = track["id"]

        return latest_id

    def download_cover(self, save_file, cover_url, url_is_absolute=False):
        if os.path.exists(NextcloudMusicClient.get_cover_from_album_id(save_file)):
            # Skipping download, cover already exists
            return
        server=self._server
        # If the url is absolute, take urls off the server
        if url_is_absolute:
            url_parts = urlparse(self._server)
            server = f"{url_parts.scheme}://{url_parts.netloc}"
        cover_url_full = f"{server}{cover_url}"
        print(f"Downloading cover at {cover_url_full}")
        response = requests.get(cover_url_full, auth=self._auth)
        if response.status_code != 200:
            print(f"Could not download cover at url code {response.status_code} for path {cover_url_full}")
        if not os.path.exists(NextcloudMusicClient.get_cache_dir()):
            try:
                os.makedirs(NextcloudMusicClient.get_cache_dir())
            except FileExistsError:
                pass  # Expected to be possible, this is called from multiple threads
        with open(NextcloudMusicClient.get_cover_from_album_id(save_file), "wb") as cover_file:
            cover_file.write(response.content)

    def download_cover_async_generic(self, album_id, cover_url, widget, callback):
        task = Gio.Task.new(widget, None, callback, None)
        task.set_return_on_cancel(False)
        task.set_task_data(album_id)
        task.run_in_thread(self.download_cover_sync)

    def download_cover_async(self, album_id, cover_url, widget):
        self.download_cover_async_generic(album_id, cover_url, widget, self.cover_downloaded)

    def download_cover_sync(self, task, source_object, task_data, cancellable):
        album_id = task.get_task_data()
        if album_id not in self._album_urls_by_id:
            # We are mid update
            return
        cover_url = self._album_urls_by_id[album_id]
        if not cover_url:
            task.return_value(False)
            return

        self.download_cover(album_id, cover_url, url_is_absolute=True)
        task.return_value(album_id)

    def get_cover(self, album_list_item):
        album_details = self.album_details(album_list_item)
        if not album_details:
            # FIXME if album_details doesn't return, why is that
            return "🤷"  # Well that's not a path
        album_id = album_details["id"]
        return NextcloudMusicClient.get_cover_from_album_id(album_id)

    def cover_downloaded(self, album_tile, task, baz):
        album_id = task.get_task_data()
        album_tile.set_cover(NextcloudMusicClient.get_cover_from_album_id(album_id))

#########################


    def download_playlist_cover_async(self, playlist_id, cover_url, widget):
        task = Gio.Task.new(widget, None, self.playlist_cover_downloaded, None)
        task.set_return_on_cancel(False)
        task.set_task_data(playlist_id)
        task.run_in_thread(self.download_playlist_cover_sync)

    def download_playlist_cover_sync(self, task, source_object, task_data, cancellable):
        playlist_id = task.get_task_data()
        cover_url = None
        for playlist in self.playlists:
            if playlist.playlist_id == playlist_id:
                cover_url = playlist.cover

        if not cover_url:
            task.return_value(False)
            return

        self.download_cover(f"playlist_{playlist_id}", cover_url, url_is_absolute=True)
        task.return_value(playlist_id)

    def get_playlist_cover(self, playlist_id):
        # TODO I guess remove these, they aren't coming back
        return f"/tmp/net.rosebirch.nextgroove/cover_playlist_{playlist_id}"

    def playlist_cover_downloaded(self, requesting_widget, task, baz):
        playlist_id = task.get_task_data()
        requesting_widget.set_cover(self.get_playlist_cover(playlist_id))

    def collection_async(self, callback):
        print("Starting async call")
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.collection_sync)

    def collection_sync(self, task, source_object, task_data, cancellable):
        collection = self.update_collection()
        task.return_value(collection)

    def playlist_async(self, callback):
        print("Starting async call for playlists")
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.playlist_sync)

    def playlist_sync(self, task, source_object, task_data, cancellable):
        playlists = self.update_playlists()
        task.return_value(playlists)

    def update_playlists(self):
        try:
            response = self._playlists()
            if response.status_code != 200:
                print(f"return code was {response.status_code}")
                return None
            playlists = json.loads(response.text)
            self.parse_playlist_json(playlists)
            return self.playlists
        except requests.exceptions.RequestException as e:
            # Updating playlists occurs at same time as collection is updated.
            # As the error is thrown back for display, ignore this error
            # as _likely_ it will be the same error as collection error.
            print(f"Exception in updating collection {e}")
            return None

    def parse_playlist_json(self, playlist_json):
        self.playlists.remove_all()
        for playlist in playlist_json:
            playlist_name = playlist['name']
            playlist_id = playlist['id']
            # Created and Updated and cover seems missing now?
            #updated = playlist['updated']
            #created = playlist['created']
            #cover = playlist['cover']
            # No longer have track_ids, it's tracks and we now need to get IDs from that object
            track_ids = []
            for track in playlist['tracks']:
                track_ids.append(track['id'])
            item = PlaylistItem(playlist_name, track_ids, playlist_id, None, None, None)
            self.playlists.append(item)


    def get_song(self, song_id):
        # TODO check if already exists and use a cache dir
        # TODO also add some method to clear cache cos could get big
        print(f"Downloading song from {self._base_url}/files/{song_id}/download")
        response = requests.get(
            f"{self._base_url}/files/{song_id}/download", auth=self._auth
        )
        if not os.path.exists(f"/tmp/net.rosebirch.nextgroove/"):
            try:
                os.makedirs(f"/tmp/net.rosebirch.nextgroove/")
            except FileExistsError:
                pass  # Expected to be possible, this is called from multiple threads
        song_location = f"/tmp/net.rosebirch.nextgroove/{song_id}"
        with open(song_location, "wb") as song_file:
            song_file.write(response.content)
        return os.path.abspath(song_location)

    def get_song_async(self, song_id, song_title, callback):
        print("Starting async song download call")
        self.song_title_last_callback = song_title
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.set_task_data(song_id)
        task.run_in_thread(self.get_song_sync)

    def get_song_sync(self, task, source_object, task_data, cancellable):
        song_id = task.get_task_data()
        song_file = self.get_song(song_id)
        task.return_value(song_file)

    def create_new_playlist_async(self, playlist_name, songs, callback):
        print("Starting multistage playlist creation calls")
        self.playlist_save_buffer = []
        self.playlist_save_buffer.append({"songs": songs, "name": playlist_name})
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.set_task_data(0)
        task.run_in_thread(self.create_new_playlist_sync)

    def create_new_playlist_sync(self, task, source_object, task_data, cancellable):
        playlist_index = task.get_task_data()
        playlist_buffer = self.playlist_save_buffer[playlist_index]
        playlist_name = playlist_buffer["name"]
        songs = playlist_buffer["songs"]
        in_data = {"name": playlist_name}
        response = requests.post(
            f"{self._base_url}/playlists", auth=self._auth, json=in_data
        )
        if response.status_code != 200:
            print(f"Got {response.status_code} http status from POST at playlists api endpoint")
            return
        # Now need to add song
        playlist_create_response = json.loads(response.text)
        if "id" not in playlist_create_response:
            print("Unexpected response from /api/playlists POST")
            return
        new_playlist_id = playlist_create_response["id"]
        track_ids = []
        for song in songs:
            print(f"Adding song {song.title} and id {song.get_track_id()} to playlist")
            track_ids.append(str(song.get_track_id()))
        tracks_csv = ",".join(track_ids)
        track_data = {"track": tracks_csv}
        response = requests.post(
            f"{self._base_url}/playlists/{new_playlist_id}/add", auth=self._auth, json=track_data
        )
        # TODO check output


    def delete_playlist_async(self, playlist_id):
        print(f"Deleting playlist with ID {playlist_id}")
        task = Gio.Task.new(self, None, self.call_update_playlist, None)
        task.set_return_on_cancel(False)
        task.set_task_data(playlist_id)
        task.run_in_thread(self.delete_playlist_sync)

    def delete_playlist_sync(self, task, source_object, task_data, cancellable):
        playlist_id = task.get_task_data()
        response = requests.delete(
            f"{self._base_url}/playlists/{playlist_id}", auth=self._auth
        )
        if response.status_code != 200:
            print(f"Got {response.status_code} http status from POST at playlists api endpoint")
            return

    def call_update_playlist(self, one, two, three):
        self.playlist_async(None)

    def get_cache_dir():
        if 'XDG_CACHE_HOME' in os.environ:
            return os.environ['XDG_CACHE_HOME']
        else:
            return "/tmp/net.rosebirch.nextgroove/"

    def get_cover_from_album_id(album_id):
        cache_dir = NextcloudMusicClient.get_cache_dir()
        return f"{cache_dir}/cover_{album_id}"
