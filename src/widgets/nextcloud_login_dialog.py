from gettext import gettext as _
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from enum import IntEnum, auto
from threading import Thread
from typing import Optional

from .login_request_result import LoginRequestResult

class LoginDialogMode(IntEnum):
    NORMAL = auto()
    REAUTHENTICATE = auto()
    SECRET_SERVICE_FAILURE = auto()


@Gtk.Template(resource_path="/net/rosebirch/nextgroove/gtk/nextcloud_login_dialog.ui")
class NextcloudLoginDialog(Adw.Dialog):
    __gtype_name__ = "NextcloudLoginDialog"

    CHECK_LOGIN_INTERVAL = 1000

    _toolbar_view: Adw.ToolbarView = Gtk.Template.Child()
    _stack: Gtk.Stack = Gtk.Template.Child()

    _intro: Adw.StatusPage = Gtk.Template.Child()
    _secret_service_failure: Adw.StatusPage = Gtk.Template.Child()
    _entry: Adw.ToastOverlay = Gtk.Template.Child()
    _self_signed_certificate_handling: Adw.StatusPage = Gtk.Template.Child()
    _loading: Adw.StatusPage = Gtk.Template.Child()
    _finished: Adw.StatusPage = Gtk.Template.Child()

    _url_continue_button: Gtk.Button = Gtk.Template.Child()
    _url_entry: Adw.EntryRow = Gtk.Template.Child()

    _instance_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, mode: LoginDialogMode, settings, client) -> None:
        super().__init__()
        self.__mode = mode
        self.__settings = settings
        self.__client = client
        self.__timeout_id = None
        if mode == LoginDialogMode.SECRET_SERVICE_FAILURE:
            self._stack.set_visible_child(self._secret_service_failure)
        elif mode == LoginDialogMode.REAUTHENTICATE:
            endpoint = self.__settings.get_string("server")
            if endpoint != "":
                self._url_entry.set_text(endpoint)
            self.__attempt_login()


        self.connect("closed", lambda _o: self.__on_close())

    @Gtk.Template.Callback()
    def _on_intro_continue_clicked(self, _button: Gtk.Button) -> None:
        self._stack.set_visible_child(self._entry)
        self._url_continue_button.set_sensitive(False)
        endpoint = self.__settings.get_string("server")
        if endpoint != "":
            self._url_entry.set_text(endpoint)
        self._url_entry.grab_focus()
        self._url_entry.set_position(-1)

    @Gtk.Template.Callback()
    def _on_entry_continue_clicked(self, _button: Gtk.Button) -> None:
        self.__attempt_login()

    @Gtk.Template.Callback()
    def _on_url_entry_changed(self, _entry: Gtk.Editable) -> None:
        self._url_continue_button.set_sensitive(self.__url_entry_valid())

    @Gtk.Template.Callback()
    def _on_url_entry_activated(self, _entry: Gtk.Entry) -> None:
        if self.__url_entry_valid():
            self.__attempt_login()

    @Gtk.Template.Callback()
    def _open_faq(self, _button: Gtk.Button) -> None:
        app = Gio.Application.get_default()
        if not app:
            return None
        window = app.get_active_window()
        Gtk.show_uri(
            window,
            "https://gitlab.gnome.org/World/iotas/-/wikis/nextcloud-notes",
            Gdk.CURRENT_TIME,
        )

    @Gtk.Template.Callback()
    def _on_done_clicked(self, _button: Gtk.Button) -> None:
        self.close()

    def __on_close(self) -> None:
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None


    def __on_login_success(self) -> None:
        pass

    def __on_initial_sync_finished(self) -> None:
        self._stack.set_visible_child(self._finished)
        self._toolbar_view.set_reveal_top_bars(False)

        def removeprefix(instr, prefix):
            return instr[len(prefix) :] if instr.startswith(prefix) else instr

        clean_url = removeprefix(self.__server_url, "https://")
        clean_url = removeprefix(clean_url, "http://")

        self._instance_label.set_text(clean_url)

    def __url_entry_valid(self) -> bool:
        valid = False
        entry_text = self.__get_sanitised_url_entry()
        try:
            valid = GLib.uri_is_valid(entry_text, GLib.UriFlags.NONE)
        except GLib.GError:
            pass
        # GLib's Uri.is_valid appears to allow eg. http:someurl.com
        if valid:
            scheme = GLib.uri_peek_scheme(entry_text)
            if scheme not in ("http", "https") or not entry_text.startswith(f"{scheme}://"):
                valid = False
        return valid

    def __wait_and_check_success(self) -> None:
        print("start timer")
        self.__timeout_id = GLib.timeout_add(self.CHECK_LOGIN_INTERVAL, self.__check_success)

    def __check_success(self) -> None:
        self.__timeout_id = None

        def thread_do() -> None:
            assert self.__endpoint
            assert self.__token
            login_success = not self.__client.check_for_login_success(self.__endpoint, self.__token)
            if login_success:
                print("Got a success")
                GLib.idle_add(self.__on_initial_sync_finished)
            else:
                GLib.idle_add(self.__wait_and_check_success)



        thread = Thread(target=thread_do)
        thread.daemon = True
        thread.start()

    def __attempt_login(self) -> None:
        self._stack.set_visible_child(self._loading)
        self._loading.set_description("")
        # Translators: Title
        self._loading.set_title(_("Connecting"))

        self.__server_url = self.__get_sanitised_url_entry()

        def thread_do() -> None:
            # Using instead of getting parent due to __attempt_login being called in constructor
            # for reauthentication
            app = Gio.Application.get_default()
            window = app.get_active_window()
            #(result, endpoint, token) = self.__sync_manager.start_login(self.__server_url, window)
            (result, endpoint, token) = self.__client.start_login(self.__server_url, window)
            GLib.idle_add(self.__handle_login_initialisation, result, endpoint, token)

        thread = Thread(target=thread_do)
        thread.daemon = True
        thread.start()

    def __handle_login_initialisation(
        self, result, endpoint: Optional[str], token: Optional[str]
    ) -> None:
        if result == LoginRequestResult.SUCCESS:
            # Translators: Title
            self._loading.set_title(_("Waiting for Login"))
            # Translators: Description
            self._loading.set_description(_("Complete the authentication in your browser"))
            self.__endpoint = endpoint
            self.__token = token
            self.__wait_and_check_success()
        elif result == LoginRequestResult.FAILURE_SELF_SIGNED_SSL:
            self._stack.set_visible_child(self._self_signed_certificate_handling)
        else:
            self._stack.set_visible_child(self._entry)
            # Set the failed URL back into try text entry. This is to make any URI scheme
            # prefixing that has been done clear to the user.
            self._url_entry.set_text(self.__server_url)
            self._url_entry.set_position(-1)
            self._url_entry.grab_focus()

            if result == LoginRequestResult.FAILURE_CERTIFICATE:
                # Translators: Description, notification
                msg = _("Failed to start login with possible certificate issue")
            else:
                # Translators: Description, notification
                msg = _("Failed to start login. Wrong address?")

            toast = Adw.Toast.new(msg)
            self._entry.add_toast(toast)

    def __get_sanitised_url_entry(self) -> str:
        entry_text = self._url_entry.get_text().strip().strip("/")
        scheme = GLib.uri_peek_scheme(entry_text)
        if entry_text != "" and scheme is None:
            entry_text = f"https://{entry_text}"
        return entry_text

