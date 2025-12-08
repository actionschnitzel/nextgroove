pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'nextgroove'
gnome = import('gnome')

gnome.compile_resources('nextgroove',
  'nextgroove.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'nextgroove.in',
  output: 'nextgroove',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

nextgroove_sources = [
  '__init__.py',
  'albumtile.py',
  'client.py',
  'controls.py',
  'main.py',
  'models/albumlistitem.py',
  'models/artist.py',
  'models/login_request_result.py',
  'models/playlist.py',
  'models/queueitem.py',
  'mpris.py',
  'settings.py',
  'widgets/album_header.py',
  'widgets/nextcloud_login_dialog.py',
  'widgets/play_stats_dialog.py',
  'widgets/playlist_header.py',
  'widgets/playlist_row.py',
  'widgets/queue_page.py',
  'widgets/song_row.py',
  'widgets/stats_row.py',
  'window.py'
]

install_data(nextgroove_sources, install_dir: moduledir)
