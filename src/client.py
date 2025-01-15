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

    def __init__(self, server, user, token):
        super().__init__()
        self._base_url = f"{server}/index.php/apps/music/api"
        self._auth = HTTPBasicAuth(user, token)
        self.albums = Gio.ListStore()

    def _collection(self):
        return requests.get(f"{self._base_url}/collection", auth=self._auth)

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
            # FIXME remove but I'm lazy, let's fix for one first
            break

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

