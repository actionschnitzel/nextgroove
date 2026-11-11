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

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Secret', '1')

import logging
import requests
import json
import os
import threading
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from gi.repository import GObject, Gio, GLib, Gtk, Gdk, Secret
from .albumlistitem import AlbumListItem
from .playlist import PlaylistItem
from .queueitem import QueueItem
from .login_request_result import LoginRequestResult


class NextcloudMusicClient(GObject.Object):

    TMP_DIR = "/tmp/io.github.actionschnitzel.actiongroovenc/"
    AGENT_HEADERS = {"User-Agent": "ActionGrooveNC/0.5.1"}
    LOGIN_ENDPOINT = "index.php/login/v2"
    SECRET_SCHEMA = Secret.Schema.new(
        "io.github.actionschnitzel.ActionGrooveNC",
        Secret.SchemaFlags.NONE,
        {"service": Secret.SchemaAttributeType.STRING},
    )
    SECRET_ATTRIBUTES = {"service": "nextcloud"}



    collection = None
    albums = None
    albums_before_sorting = None
    _server = None
    _album_urls_by_id = None
    artist_name_by_id = None
    album_name_by_id = None
    song_title_last_callback = None
    playlists = None

    def __init__(self, settings):
        super().__init__()
        self.__settings = settings
        self.albums = Gio.ListStore()
        self.albums_before_sorting = Gio.ListStore()
        self._album_urls_by_id = {}
        self.artist_name_by_id = {}
        self.album_name_by_id = {}
        self.playlists = Gio.ListStore()
        self.playlist_save_buffer = []
        self.last_error = ""
        self.__migrate_secrets()

    @property
    def cookie_headers(self):
        return self.AGENT_HEADERS | {"Cookie": f"nc_username={self.__auth().username}; nc_token={self.__auth().password}"}


    def initialized(self):
        """If we haven't tried a login ever, then this won't ever connect, let's check for that."""
        return self.__server() != ""


    def __cache(self):
        return self.__settings.get_boolean("cache")

    def __migrate_secrets(self):
        user = self.__settings.get_string("user")
        old_token = self.__settings.get_string("token")
        if old_token in (None, ""):
            logging.debug("Token already migrated: no action")
            # Already migrated
            return

        success = False
        try:
            item_id = "io.github.actionschnitzel.ActionGrooveNC: {}".format(user)
            success = Secret.password_store_sync(
                self.SECRET_SCHEMA,
                self.SECRET_ATTRIBUTES,
                Secret.COLLECTION_DEFAULT,
                item_id,
                old_token,
                None,
            )
        except Exception as e:
            logging.error(f"Failed to store password: {e}")
            return
        logging.info("Migrated to secret store.")
        self.__settings.set_string("token", "")
        return success


    def set_token(self, token):
        user = self.__settings.get_string("user")
        success = False
        try:
            item_id = "io.github.actionschnitzel.ActionGrooveNC: {}".format(user)
            success = Secret.password_store_sync(
                self.SECRET_SCHEMA,
                self.SECRET_ATTRIBUTES,
                Secret.COLLECTION_DEFAULT,
                item_id,
                token,
                None,
            )

        except Exception as e:
            logging.error(f"Failed to store password: {e}")
            return
        logging.info("Stored new token")


    def __auth(self):
        token = Secret.password_lookup_sync(self.SECRET_SCHEMA, self.SECRET_ATTRIBUTES, None)
        return HTTPBasicAuth(self.__settings.get_string("user"), token)


    def __server(self):
        return self.__settings.get_string("server")

    def __base_url(self):
        return f"{self.__server()}/index.php/apps/music/api"

    def _collection(self):
        return requests.get(f"{self.__base_url()}/collection", headers=self.cookie_headers, auth=self.__auth(), timeout=5)

    def _playlists(self):
        return requests.get(f"{self.__base_url()}/playlists", headers=self.cookie_headers, auth=self.__auth(), timeout=5)

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
        logging.error("ERROR client.album_details could not find an album")
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
        logging.error(f"get_track_from_id: Could not find track_id {song_id}")
        return None

    def get_artist_id_for_album_list_item(self, album_list_item):
        for artist in self.collection:
            if artist["name"] == album_list_item.artist:
                return artist["id"]
        logging.error("client.get_artist_id_for_album_list_item could not find artist")
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
                logging.error(f"return code was {response.status_code}")
                # Send errors back for toast on welcome page
                return f"Error: got HTTP status code {response.status_code} when checking collection"
            self.collection = json.loads(response.text)
            self.update_albums()
            return self.collection
        except requests.exceptions.RequestException as e:
            # Send errors back for toast on welcome page
            logging.error(f"Exception in updating collection {e}")
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

        logging.info(f"Retrieved albums and we have {len(self.albums_before_sorting)} albums")
        for album in sorted(
            self.albums_before_sorting,
            key=lambda item: (item.album.lower(), item.artist.lower()),
        ):
            self.albums.append(album)
        logging.info(f"Sorted albums and we have {len(self.albums)} albums")
        self.albums_before_sorting = None

    def download_cover(self, save_file, cover_url, url_is_absolute=False):
        if os.path.exists(NextcloudMusicClient.get_cover_from_album_id(save_file)):
            # Skipping download, cover already exists
            return
        server=self.__server()
        # If the url is absolute, take urls off the server
        if url_is_absolute:
            url_parts = urlparse(self.__server())
            server = f"{url_parts.scheme}://{url_parts.netloc}"
        cover_url_full = f"{server}{cover_url}"
        logging.info(f"Downloading cover at {cover_url_full}")
        response = requests.get(cover_url_full, headers=self.cookie_headers, auth=self.__auth(), timeout=5)
        if response.status_code != 200:
            logging.error(f"Could not download cover at url code {response.status_code} for path {cover_url_full}")
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
        return f"/tmp/io.github.actionschnitzel.actiongroovenc/cover_playlist_{playlist_id}"

    def playlist_cover_downloaded(self, requesting_widget, task, baz):
        playlist_id = task.get_task_data()
        requesting_widget.set_cover(self.get_playlist_cover(playlist_id))

    def collection_async(self, callback):
        logging.debug("Starting async call")
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.collection_sync)

    def collection_sync(self, task, source_object, task_data, cancellable):
        collection = self.update_collection()
        task.return_value(collection)

    def playlist_async(self, callback):
        logging.debug("Starting async call for playlists")
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
                logging.error(f"return code was {response.status_code}")
                return None
            playlists = json.loads(response.text)
            self.parse_playlist_json(playlists)
            return self.playlists
        except requests.exceptions.RequestException as e:
            # Updating playlists occurs at same time as collection is updated.
            # As the error is thrown back for display, ignore this error
            # as _likely_ it will be the same error as collection error.
            logging.error(f"Exception in updating collection {e}")
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


    @staticmethod
    def strip_id3v2(data):
        if len(data) < 10 or data[:3] != b"ID3":
            return data
        size = 0
        for byte in data[6:10]:
            size = (size << 7) | (byte & 0x7F)
        footer = 10 if data[5] & 0x10 else 0
        return data[10 + size + footer:]

    def get_song(self, song_id):
        song_location = self.song_path(song_id)
        if os.path.exists(song_location):
            logging.info(f"Using cached song from {song_location}")
            return os.path.abspath(song_location)

        logging.info(f"Downloading song from {self.__base_url()}/files/{song_id}/download and saving to {song_location}")
        response = requests.get(
            f"{self.__base_url()}/files/{song_id}/download", auth=self.__auth(), timeout=15, headers=self.cookie_headers
        )
        if not response.ok:
            raise Exception(f"Got status {response.status_code} from downloading song")

        with open(song_location, "wb") as song_file:
            song_file.write(self.strip_id3v2(response.content))
        return os.path.abspath(song_location)

    def get_song_async(self, song_id, song_title, callback):
        logging.debug("Starting async song download call")
        self.song_title_last_callback = song_title
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.set_task_data(song_id)
        task.run_in_thread(self.get_song_sync)

    def get_song_sync(self, task, source_object, task_data, cancellable):
        song_id = task.get_task_data()
        try:
            song_file = self.get_song(song_id)
            task.return_value(song_file)
        except Exception as e:
            logging.error(f"Error during song download: {str(e)}")
            self.last_error = str(e)
            task.return_error(GLib.Error(str(e)))

    def create_new_playlist_async(self, playlist_name, songs, callback):
        logging.debug("Starting multistage playlist creation calls")
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
            f"{self.__base_url()}/playlists", auth=self.__auth(), json=in_data, headers=self.cookie_headers
        )
        if response.status_code != 200:
            logging.error(f"Got {response.status_code} http status from POST at playlists api endpoint")
            return
        # Now need to add song
        playlist_create_response = json.loads(response.text)
        if "id" not in playlist_create_response:
            logging.error("Unexpected response from /api/playlists POST")
            return
        new_playlist_id = playlist_create_response["id"]
        track_ids = []
        for song in songs:
            logging.info(f"Adding song {song.title} and id {song.get_track_id()} to playlist")
            track_ids.append(str(song.get_track_id()))
        tracks_csv = ",".join(track_ids)
        track_data = {"track": tracks_csv}
        response = requests.post(
            f"{self.__base_url()}/playlists/{new_playlist_id}/add", auth=self.__auth(), json=track_data, headers=self.cookie_headers
        )
        # TODO check output


    def delete_playlist_async(self, playlist_id):
        logging.info(f"Deleting playlist with ID {playlist_id}")
        task = Gio.Task.new(self, None, self.call_update_playlist, None)
        task.set_return_on_cancel(False)
        task.set_task_data(playlist_id)
        task.run_in_thread(self.delete_playlist_sync)

    def delete_playlist_sync(self, task, source_object, task_data, cancellable):
        playlist_id = task.get_task_data()
        response = requests.delete(
            f"{self.__base_url()}/playlists/{playlist_id}", auth=self.__auth(), headers=self.cookie_headers
        )
        if response.status_code != 200:
            logging.error(f"Got {response.status_code} http status from POST at playlists api endpoint")
            return

    def fill_song_playlist_menu(self, menu, action_name):
        """Rebuild the trailing playlist submenu of a song menu."""
        while menu.get_n_items() > 1:
            menu.remove(menu.get_n_items() - 1)
        if self.playlists.get_n_items() == 0:
            return
        submenu = Gio.Menu()
        for playlist in self.playlists:
            item = Gio.MenuItem.new(playlist.playlist_name, None)
            item.set_action_and_target_value(action_name, GLib.Variant.new_string(str(playlist.playlist_id)))
            submenu.append_item(item)
        menu.append_submenu("_Add to playlist", submenu)

    def add_track_to_playlist_async(self, playlist_id, track_id):
        threading.Thread(target=self.add_track_to_playlist_sync, args=(playlist_id, track_id), daemon=True).start()

    def add_track_to_playlist_sync(self, playlist_id, track_id):
        response = requests.post(
            f"{self.__base_url()}/playlists/{playlist_id}/add", auth=self.__auth(),
            json={"track": str(track_id)}, headers=self.cookie_headers
        )
        if response.status_code != 200:
            logging.error(f"Got {response.status_code} http status adding track to playlist {playlist_id}")

    def call_update_playlist(self, one, two, three):
        self.playlist_async(None)

    def get_cache_dir():
        if 'XDG_CACHE_HOME' in os.environ:
            return os.environ['XDG_CACHE_HOME']
        else:
            return os.path.expanduser("~/.cache")

    def song_path(self, song_id):
        base_dir = NextcloudMusicClient.TMP_DIR
        if self.__cache():
            base_dir = NextcloudMusicClient.get_cache_dir()
        song_dir = os.path.join(base_dir, "songs")
        if not os.path.isdir(song_dir):
            logging.info(f"Making song cache_directory {song_dir}")
            os.makedirs(song_dir)
        full_path = os.path.join(song_dir, str(song_id))
        return full_path

    def get_cover_from_album_id(album_id):
        cache_dir = NextcloudMusicClient.get_cache_dir()
        return f"{cache_dir}/cover_{album_id}"

    def start_login(self, server_url, window):
        login_url = f"{server_url}/{self.LOGIN_ENDPOINT}"
        logging.debug(f"Want to send a login request to {login_url}")
        try:
            response = requests.post(
                login_url, headers=self.AGENT_HEADERS
            )
        except requests.ConnectionError as e:
            logging.error(e)
            return (LoginRequestResult.FAILURE_GENERIC, None, None)
        if not response.ok:
            logging.error("Failed to start login")
            return (LoginRequestResult.FAILURE_GENERIC, None, None)
        response_json = json.loads(response.text)

        poll_url = response_json["poll"]["endpoint"]
        token_data = {"token": response_json["poll"]["token"]}
        user_auth_url = response_json["login"]

        # TODO change this to not need the window passed in
        def open_url_in_browser(window, response: dict) -> None:
            Gtk.show_uri(window, user_auth_url, Gdk.CURRENT_TIME)

        GLib.idle_add(open_url_in_browser, window, response)
        return (LoginRequestResult.SUCCESS, poll_url, token_data)

    def check_for_login_success(self, poll_url, token_data):
        logging.debug("Checking poll url")
        try:
            poll_response = requests.post(
                poll_url, headers=self.AGENT_HEADERS, data=token_data
            )
        except:
            return True
        if poll_response.status_code != 200:
            return True

        poll_json = json.loads(poll_response.text)
        if "server" in poll_json:
            logging.info("Login success, saving credentials")
            server = poll_json["server"]
            user = poll_json["loginName"]
            password = poll_json["appPassword"]
            self.__settings.set_string("server", server)
            self.__settings.set_string("user", user)
            self.set_token(password)
            return False
        return True

    def scrobble(self, track_id):
        logging.info(f"Want to scrobble id {track_id}")
        scrobble_url = f"{self.__base_url()}/tracks/{track_id}/scrobble"
        try:
            scrobble_response = requests.post(
                scrobble_url, headers=self.cookie_headers, auth=self.__auth(), allow_redirects=False,
            )
            logging.debug(f"Scrobble return code: {scrobble_response.status_code}")
        except Exception as e:
            logging.debug(f"Scrobble error: {str(e)}")
            return True

    def scrobble_async(self, track_id, widget):
        task = Gio.Task.new(widget, None, None, None)
        task.set_return_on_cancel(False)
        task.set_task_data(track_id)
        task.run_in_thread(self.scrobble_sync)

    def scrobble_sync(self, task, source_object, task_data, cancellable):
        track_id = task.get_task_data()
        self.scrobble(track_id)

    def get_ampache_summary(self):
        # Note this uses the ampache API, base url cannot be used.
        stats_url = f"{self.__server()}/index.php/apps/music/ampache/internal?action=songs"
        stats_response = requests.get(
                stats_url, headers=self.cookie_headers, auth=self.__auth()
            )
        if stats_response.status_code != 200:
            logging.error("Failed to get stats")
            return None

        self.songs_data = json.loads(stats_response.text)

    def get_ampache_summary_async(self, widget, callback):
        task = Gio.Task.new(widget, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.get_ampache_summary_sync)

    def get_ampache_summary_sync(self, task, source_object, task_data, cancellable):
        self.get_ampache_summary()

    def retreive_summary(self):
        return self.songs_data
