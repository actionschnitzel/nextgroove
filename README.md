# nextcloudmusic

Limited GNOME based client for Nextcloud Music created as a holiday programming
project. Check the current capabilities section.

## Current Capabilities

 - Connects to a Nextcloud instance of your choice via normal API tokens (does not use subsonic/ampache endpoints but the [Nextcloud ones](https://github.com/owncloud/music?tab=readme-ov-file#api)
 - Configurable from a settings page, *but client is not currently reloaded: update the settings then restart the program.*
 - View albums in a grid, most recently uploaded first.
 - Click an album to play an album.
 - The current play queue is viewable showing what song is currently playing in bold.

## TODO

Just some notes on what I want to focus on next, not an exhaustive list of the
many, many, flaws that need to be fixed!

 - [ ] Scrolling on the songs
 - [x] clicking a song and play the song
 - [x] ordering (albums)
 - [ ] making the collection view not look like arse (tabular?)
 - [ ] tab view at top level, to switch between views:
   - [x] Album view
   - [ ] All song view (i.e. current one)
   - [ ] Playlists
   - [ ] Podcasts
- [x] Some sidebar to show the queue (kinda - just did a tab)
- [x] oh yeah a queuing system in general (added to a queue, but doesn't work yet)
- [x] media player controls
- [ ] mpris
- [ ] update client auth on settings window closed
- [x] hide token
