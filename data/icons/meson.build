application_id = 'net.rosebirch.nextgroove'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / ('@0@.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)

install_data(
  scalable_dir / 'share-alt-symbolic.svg',
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)
install_data(
  scalable_dir / 'checkmark.svg',
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)


symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)