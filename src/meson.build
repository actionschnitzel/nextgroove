pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'nextcloudmusic'
gnome = import('gnome')

gnome.compile_resources('nextcloudmusic',
  'nextcloudmusic.gresource.xml',
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
  input: 'nextcloudmusic.in',
  output: 'nextcloudmusic',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

nextcloudmusic_sources = [
  '__init__.py',
  'albumtile.py',
  'models/albumlistitem.py',
  'client.py',
  'controls.py',
  'main.py',
  'models/playlist.py',
  'models/queueitem.py',
  'window.py',
  'settings.py'
]

install_data(nextcloudmusic_sources, install_dir: moduledir)
