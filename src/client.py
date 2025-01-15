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
from requests.auth import HTTPBasicAuth
from gi.repository import GObject, Gio
from .albumlistitem import AlbumListItem

class NextcloudMusicClient(GObject.Object):

    _auth = None
    _base_url = None
    collection = None
    albums = None
    _server = None
    _album_urls_by_id = None

    def __init__(self, server, user, token):
        super().__init__()
        self._base_url = f"{server}/index.php/apps/music/api"
        self._auth = HTTPBasicAuth(user, token)
        self.albums = Gio.ListStore()
        self._server = server
        self._album_urls_by_id = {}

    def _collection(self):
        return requests.get(f"{self._base_url}/collection", auth=self._auth)

    def album_details(self, album_list_item):
        for artist in self.collection:
            if artist['name'] == album_list_item.artist:
                for album in artist['albums']:
                    if album['name'] == album_list_item.album:
                        return album
        print("UH OH couldn't find album?")
        return None

    def validate(self):
        # FIXME remove this call, this is just testing the function prior to getting the async shit in place
        self.update_collection()
        try:
            response = self._collection()
            if response.status_code == 200:
                return True
            else:
                return False
        except:
            # TODO better error handling and user messaging
            return False

    def validate_async(self, callback):
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.validate_sync)

    def validate_sync(self, task, source_object, task_data, cancellable):
        valid = self.validate()
        task.return_value(valid)

    def update_collection(self):
        try:
            response = self._collection()
            if response.status_code != 200:
                print(f"return code was {response.status_code}")
                return None
            self.collection = json.loads(response.text)
            self.update_albums()
            return self.collection
        except requests.exceptions.RequestException as e:
            # TODO better error handling and user messaging
            print(f"Exception in updating collection {e}")
            return None

    def update_albums(self):
        # FIXME remove previous ones - cannot see how to clear them
        for artist in self.collection:
            artist_string = artist['name']
            for album in artist['albums']:
                album_string = album['name']
                album_item = AlbumListItem(artist_string, album_string)
                self.albums.append(album_item)
                if album['cover']:
                    self._album_urls_by_id[album['id']] = album['cover']
                    keys = self._album_urls_by_id.keys()
                    print(f"Current keys in albums: {keys}")
                    self.download_cover_async(album['id'], album['cover'])
                #print(album)
            # FIXME remove but I'm lazy, let's fix for one first
            #break


    def download_cover(self, album_id, cover_url):
        #print(f"cover at {cover_url}")
        cover_url_full = f"{self._server}{cover_url}"
        #print(f"full url {cover_url_full}")
        response = requests.get(cover_url_full, auth=self._auth)
        if response.status_code != 200:
            print("Could not download cover at url code {response.status_code}")
        if not os.path.exists(f"/tmp/net.rosebirch.nextcloudmusic/"):
            os.makedirs(f"/tmp/net.rosebirch.nextcloudmusic/")
        with open(f"/tmp/net.rosebirch.nextcloudmusic/cover_{album_id}", "wb") as cover_file:
            cover_file.write(response.content)

    def download_cover_async(self, album_id, cover_url):
        """no callback needed"""
        task = Gio.Task.new(self, None, None, None)
        task.set_return_on_cancel(False)
        task.set_task_data(album_id)
        task.run_in_thread(self.download_cover_sync)

    def download_cover_sync(self, task, source_object, task_data, cancellable):
        album_id = task.get_task_data()
        cover_url = self._album_urls_by_id[album_id]
        self.download_cover(album_id, cover_url)
        task.return_value(True)

    def get_cover(self, album_list_item):
        album_details = self.album_details(album_list_item)
        album_id = album_details['id']
        return f"/tmp/net.rosebirch.nextcloudmusic/cover_{album_id}"

    def collection_async(self, callback):
        print("Starting async call")
        task = Gio.Task.new(self, None, callback, None)
        task.set_return_on_cancel(False)
        task.run_in_thread(self.collection_sync)

    def collection_sync(self, task, source_object, task_data, cancellable):
        collection = self.update_collection()
        task.return_value(collection)

    def get_song(self, song_id):
        # TODO check if already exists and use a cache dir
        # TODO also add some method to clear cache cos could get big
        print(f"Attempting to call {self._base_url}/file/{song_id}/download")
        response = requests.get(f"{self._base_url}/file/{song_id}/download", auth=self._auth)
        if not os.path.exists(f"/tmp/net.rosebirch.nextcloudmusic/"):
            os.makedirs(f"/tmp/net.rosebirch.nextcloudmusic/")
        song_location = f"/tmp/net.rosebirch.nextcloudmusic/{song_id}"
        with open(song_location, "wb") as song_file:
            song_file.write(response.content)
        return os.path.abspath(song_location)

