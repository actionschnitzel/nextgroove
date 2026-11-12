# Maintainer: Actionschnitzel <actionschnitzel@guideos.de>
pkgname=actiongroovenc
pkgver=0.6.1
pkgrel=1
pkgdesc="GNOME client for Nextcloud Music"
arch=('any')
url="https://github.com/actionschnitzel/nextgroove"
license=('GPL-3.0-or-later')
depends=('gtk4' 'libadwaita' 'glib2' 'libsecret' 'python' 'python-gobject' 'python-requests')
makedepends=('meson' 'ninja' 'gettext' 'desktop-file-utils' 'appstream' 'pkgconf')
source=("${pkgname}.tar.gz")
sha256sums=('SKIP')

build() {
  cd "$srcdir/$pkgname"
  arch-meson . build
  meson compile -C build
}

package() {
  cd "$srcdir/$pkgname"
  meson install -C build --destdir "$pkgdir"
}
