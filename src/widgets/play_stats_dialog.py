import gi
gi.require_version('Adw', '1')

from gettext import gettext as _
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from operator import itemgetter

from enum import IntEnum, auto
from threading import Thread
from typing import Optional

from .stats_row import StatsRow

import datetime
import os
import re
import json


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/play_stats_dialog.ui")
class PlayStatsDialog(Adw.Dialog):
    __gtype_name__ = "PlayStatsDialog"

    _toolbar_view: Adw.ToolbarView = Gtk.Template.Child()
    _stack: Gtk.Stack = Gtk.Template.Child()

    _intro: Adw.StatusPage = Gtk.Template.Child()
    _loading: Adw.StatusPage = Gtk.Template.Child()
    _finished_lifetime: Adw.StatusPage = Gtk.Template.Child()
    top5songslifetime: Gtk.Box = Gtk.Template.Child()
    top5albumslifetime = Gtk.Template.Child()
    top5artistslifetime = Gtk.Template.Child()

    topsong1 = Gtk.Template.Child()
    topsong2 = Gtk.Template.Child()
    topsong3 = Gtk.Template.Child()
    topsong4 = Gtk.Template.Child()
    topsong5 = Gtk.Template.Child()

    topalbum1 = Gtk.Template.Child()
    topalbum2 = Gtk.Template.Child()
    topalbum3 = Gtk.Template.Child()
    topalbum4 = Gtk.Template.Child()
    topalbum5 = Gtk.Template.Child()

    topartist1 = Gtk.Template.Child()
    topartist2 = Gtk.Template.Child()
    topartist3 = Gtk.Template.Child()
    topartist4 = Gtk.Template.Child()
    topartist5 = Gtk.Template.Child()

    topsongsheaderlabel = Gtk.Template.Child()
    topalbumsheaderlabel = Gtk.Template.Child()
    topartistsheaderlabel = Gtk.Template.Child()

    previous_picker = Gtk.Template.Child()
    _end = Gtk.Template.Child()
    sharerow = Gtk.Template.Child()
    copy_button = Gtk.Template.Child()

    def __init__(self, settings, client) -> None:
        super().__init__()
        self.__settings = settings
        self.__client = client
        # TODO remove this connection if nothing in here
        self.connect("closed", lambda _o: self.__on_close())
        self.previous_song_counts = {}
        self.share_text = ""
        self.copy_button.connect("clicked", self.__on_share_copy)

    @Gtk.Template.Callback()
    def _on_intro_continue_clicked(self, _button: Gtk.Button) -> None:
        self._stack.set_visible_child(self._loading)
        self.__client.get_ampache_summary_async(self, self.__process_summary)
    def __on_close(self):
        pass


    def __process_summary(self, foo, bar, baz):
        songs_data = self.__client.retreive_summary()
        stats_folder = os.path.join(os.environ['XDG_CACHE_HOME'], "stats")

        # If folder doesn't exist, create it
        if not os.path.isdir(stats_folder):
            os.makedirs(stats_folder)

        # Save current summary
        # This will overwrite if you do it twice in a day...
        # but if you only do this every year, not going to make a lot of difference
        current_datestr = datetime.datetime.now().date().isoformat()
        current_date_file = os.path.join(stats_folder, f"stats_snapshot_{current_datestr}.json")
        with open(current_date_file, "w") as stats_today:
            stats_today.write(json.dumps(songs_data))

        self.previous_model = Gtk.StringList()
        self.previous_model.append("Lifetime")
        self.previous_picker.set_model(self.previous_model)

        pattern = "stats_snapshot_(\\d{4}-\\d\\d-\\d\\d).json"
        for filename in sorted(os.listdir(stats_folder)):
            if re.search(pattern, filename):
                snapshot_date = re.search(pattern,filename).group(1)
                print(f"Found prev snapshot of {filename} for {snapshot_date}")
                if snapshot_date == current_datestr:
                    print(f"Ignoring {filename} as that is today's date")
                    continue
                self.previous_model.append(snapshot_date)

        self._stack.set_visible_child(self._finished_lifetime)

    def __process_summary_method(self, songrow_list, albumrow_list, artistrow_list, stack, period_text):
        songs_data = self.__client.retreive_summary()
        song_counts = {}
        album_counts = {}
        artist_counts = {}
        self.share_text = f"{period_text}\n\n"

        song_details = {}
        artist_details = {}
        album_details = {}

        previous_data = None

        for song in songs_data["song"]:

            # Record play counts
            song_id = str(song["id"])

            song_count = song["playcount"]

            # subtract previous values if they are present
            if song_id in self.previous_song_counts:
                song_count -= self.previous_song_counts[song_id]


            song_counts[song_id] = song_count

            artist_id = song["artist"]["id"]
            if artist_id not in artist_counts:
                artist_counts[artist_id] = 0
            artist_counts[artist_id] += song_count

            album_id = song["album"]["id"]
            if album_id not in album_counts:
                album_counts[album_id] = 0
            album_counts[album_id] += song_count

            # Record details
            song_details[song_id] = {"title": song["title"], "artist": song["artist"]["name"], "album": song["album"]["name"], "album_id": song["album"]["id"]}
            artist_details[artist_id] = song["artist"]["name"]
            album_details[album_id] = song["album"]["name"]


        song_counts_list = []
        for song_id in song_counts:
            song_counts_list.append((song_id, song_counts[song_id]))
        song_counts_sorted = sorted(song_counts_list, key=itemgetter(1), reverse=True)

        top_five_song_counts_sorted = song_counts_sorted[:5]

        self.share_text += "Top 5 Songs:\n"
        topsongs_list = songrow_list
        position = 1
        for song in top_five_song_counts_sorted:
            song_id = song[0]
            top_song_details = song_details[song_id]
            title = top_song_details["title"]
            artist = top_song_details["artist"]
            album = top_song_details["album"]
            album_id = top_song_details["album_id"]
            # FIXME album cover, make it not look shit and next button
            topsongs_list[position].set_details(title, f"{artist} - {album}", position, song[1], album_id)
            self.share_text += f"{position}:  {title} - {artist} ({song[1]} plays)\n"
            position += 1

        artist_counts_list = []
        for artist_id in artist_counts:
            artist_counts_list.append((artist_id, artist_counts[artist_id]))
        artist_counts_sorted = sorted(artist_counts_list, key=itemgetter(1), reverse=True)

        top_five_artist_counts_sorted = artist_counts_sorted[:5]

        self.share_text += f"\nTop 5 Artists:\n"
        topartists_list = artistrow_list
        position = 1
        for artist in top_five_artist_counts_sorted:
            artist_id = artist[0]
            played = artist[1]

            artist_name = artist_details[artist_id]
            topartists_list[position].set_details(artist_name, None, position, played, None)
            self.share_text += f"{position}:  {artist_name} ({played} plays)\n"
            position += 1


        album_counts_list = []
        for album_id in album_counts:
            album_counts_list.append((album_id, album_counts[album_id]))
        album_counts_sorted = sorted(album_counts_list, key=itemgetter(1), reverse=True)
        top_five_album_counts_sorted = album_counts_sorted[:5]

        self.share_text += f"\nTop 5 Albums:\n"
        topalbums_list = albumrow_list
        position = 1
        for album in top_five_album_counts_sorted:
            album_id = album[0]
            played = album[1]

            album_name = album_details[album_id]
            topalbums_list[position].set_details(album_name, None, position, album[1], album_id)
            self.share_text += f"{position}: {album_name} ({album[1]} plays)\n"
            position += 1

        self.share_text += "\n#NextcloudWrapped #NextGroove #Nextcloud #Wrapped"

        shortened_share_text = "\n".join(self.share_text.split("\n")[0:4]) + "\n…"
        self.sharerow.set_subtitle(shortened_share_text)
        self.sharerow.set_subtitle_lines(4)

        self._stack.set_visible_child(stack)

    @Gtk.Template.Callback()
    def _on_albums_clicked(self, foo):
        print("Albums clicked")
        self._stack.set_visible_child(self.top5albumslifetime)

    @Gtk.Template.Callback()
    def _on_artists_clicked(self, foo):
        print("Artists clicked")
        self._stack.set_visible_child(self.top5artistslifetime)

    @Gtk.Template.Callback()
    def _on_lifetime_finished(self, foo):
        self._stack.set_visible_child(self._end)

    @Gtk.Template.Callback()
    def _on_previous_selected(self, foo):
        selected = self.previous_picker.get_selected()
        selected_date = self.previous_model[selected]
        print(f"slected is {selected} {selected_date.get_string()}")
        stats_folder = os.path.join(os.environ['XDG_CACHE_HOME'], "stats")
        previous_file = os.path.join(stats_folder, f"stats_snapshot_{selected_date.get_string()}.json")

        if selected_date.get_string() == "Lifetime":
            self.previous_data = None
            self.__process_summary_method(
                [None, self.topsong1, self.topsong2, self.topsong3, self.topsong4, self.topsong5],
                [None, self.topalbum1, self.topalbum2, self.topalbum3, self.topalbum4, self.topalbum5],
                [None, self.topartist1, self.topartist2, self.topartist3, self.topartist4, self.topartist5],
                self.top5songslifetime,
                "My total Nextcloud music stats:"
            )
            self.topalbumsheaderlabel.set_label(self.topalbumsheaderlabel.get_label()+" (Lifetime)")
            self.topsongsheaderlabel.set_label(self.topsongsheaderlabel.get_label()+" (Lifetime)")
            self.topartistsheaderlabel.set_label(self.topartistsheaderlabel.get_label()+" (Lifetime)")
            return
        with open(previous_file, 'r') as prev_stats_file:
            self.previous_data = json.load(prev_stats_file)
        for song in self.previous_data["song"]:
            prev_id = song["id"]
            prev_playcount = song["playcount"]
            self.previous_song_counts[prev_id] = prev_playcount

        # TDDO fixme do new areas
        self.__process_summary_method(
            [None, self.topsong1, self.topsong2, self.topsong3, self.topsong4, self.topsong5],
            [None, self.topalbum1, self.topalbum2, self.topalbum3, self.topalbum4, self.topalbum5],
            [None, self.topartist1, self.topartist2, self.topartist3, self.topartist4, self.topartist5],
            self.top5songslifetime,
            f"My Nextcloud music stats from {selected_date.get_string()} to {datetime.datetime.now().date().isoformat()}:"
        )
        self.topalbumsheaderlabel.set_label(self.topalbumsheaderlabel.get_label()+f" (since {selected_date.get_string()})")
        self.topsongsheaderlabel.set_label(self.topsongsheaderlabel.get_label()+f" (since {selected_date.get_string()})")
        self.topartistsheaderlabel.set_label(self.topartistsheaderlabel.get_label()+f" (since {selected_date.get_string()})")
        self._stack.set_visible_child(self.top5songslifetime)

    @Gtk.Template.Callback()
    def _on_close_clicked(self, foo):
        self.close()

    def __on_share_copy(self, foo):
        clipboard = Gdk.Display.get_default().get_clipboard()
        content = gi.repository.Gdk.ContentProvider.new_for_value(self.share_text)
        clipboard.set_content(content)
        self.copy_button.set_icon_name("checkmark")
