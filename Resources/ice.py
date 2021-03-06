#!/usr/bin/env python3
#
# by Kendall Weaver <kendall@peppermintos.com>
# for Peppermint OS
# modified by Mark Greaves (PCNetSpec) <mark@peppermintos.com>
# with much appreciated code contributions by rhein
# internationalization (i18n)/gettext support by Kiyohito AOKI
# Code Rewrite, Redesign, and new GNOME Web support by PizzaLovingNerd
#
# Ice is a simple Site Specific Browser (SSB) manager for Chromium and
# Chrome specifically intended to integrate with the LXDE menu system.
# Unlike the built-in functions in the browsers, Ice boasts the ability
# to remove SSBs, validate addresses, and prevent overwriting existing
# SSBs. Special thanks to Matt Phillips <labratmatt@gmail.com> for the
# excellent pyfav library that is integrated into this application.
# ADDENDUM: Added support for Firefox (via "ice-firefox") and Vivaldi.

import bs4
import gettext
import locale
import os
import os.path
import requests
import shutil
import string
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

_HOME = os.getenv("HOME")
_ICE_DIR = "{0}/.local/share/ice".format(_HOME)
_APPS_DIR = "{0}/.local/share/applications".format(_HOME)
_PROFILES_DIR = "{0}/profiles".format(_ICE_DIR)
_FF_PROFILES_DIR = "{0}/firefox".format(_ICE_DIR)
_EPIPHANY_PROFILES_DIR = "{0}/epiphany".format(_ICE_DIR)
_ICE_ICON = "/usr/share/pixmaps/ice.png"
_ICON_DIR = "{0}/icons".format(_ICE_DIR)
_BRAVE_BIN = "/usr/bin/brave-browser"
_CHROME_BIN = "/usr/bin/google-chrome"
_CHROMIUM_BIN = "/usr/bin/chromium-browser"
_VIVALDI_BIN = "/usr/bin/vivaldi-stable"
_FIREFOX_BIN = "/usr/bin/firefox"
_EPIPHANY_BIN = "/usr/bin/epiphany"

gettext.bindtextdomain(
    'messages',
    os.path.dirname(__file__) + '/../share/ice/locale/'
    )
6
gettext.textdomain('messages')
_ = gettext.gettext

# Requisite dirs
for directory in [_ICE_DIR, _APPS_DIR, _PROFILES_DIR,
                  _FF_PROFILES_DIR, _ICON_DIR, _EPIPHANY_PROFILES_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)


class IconSel(Gtk.FileChooserDialog):

    def __init__(self):

        self.filew = Gtk.FileChooserDialog(
            title=_("Please choose an icon."),
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
        )
        self.filew.set_filename(_ICE_ICON)
        self.filew.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                               Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        self.filter1 = Gtk.FileFilter()
        self.filter1.set_name("Icons")
        self.filter1.add_mime_type("image/png")
        self.filter1.add_mime_type("image/jpeg")
        self.filter1.add_mime_type("image/gif")
        self.filter1.add_pattern("*.png")
        self.filter1.add_pattern("*.jpg")
        self.filter1.add_pattern("*.gif")
        self.filter1.add_pattern("*.xpm")
        self.filter1.add_pattern("*.svg")
        self.filew.add_filter(self.filter1)

        self.preview = Gtk.Image()
        self.filew.set_preview_widget(self.preview)
        self.filew.connect("update-preview", self.update_image)

        self.response = self.filew.run()
        if self.response == Gtk.ResponseType.OK:
            self.iconpath = self.filew.get_filename()
            self.new_icon = Pixbuf.new_from_file_at_size(self.iconpath, 32, 32)
            window.icon.set_from_pixbuf(self.new_icon)
            self.filew.destroy()
        elif self.response == Gtk.ResponseType.CANCEL:
            self.filew.destroy()

    def update_image(self, dialog):
        self.filename = dialog.get_preview_filename()
        try:
            self.pixbuf = Pixbuf.new_from_file(self.filename)
            self.preview.set_from_pixbuf(self.pixbuf)
            self.valid_preview = True
        except GLib.Error:
            self.valid_preview = False

        dialog.set_preview_widget_active(self.valid_preview)


class ErrorDialog(Gtk.Window):
    def destroy(self, button):
        self.close()

    def __init__(self, name, main, text):
        Gtk.Window.__init__(self, title=_(name))
        self.set_border_width(10)
        self.set_icon_from_file(_ICE_ICON)

        self.main_lab = Gtk.Label()
        self.main_lab.set_markup(("<b>" + _(main) + "</b>"))

        self.text_lab = Gtk.Label(
            label=_(text),
            justify=Gtk.Justification.CENTER
        )

        self.text_lab.set_line_wrap(True)

        self.close_button = Gtk.Button(label=_("Close"))
        self.close_button.connect("clicked", self.destroy)
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.box.pack_end(self.close_button, False, False, 0)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.pack_start(self.main_lab, False, False, 5)
        self.main_box.pack_start(self.text_lab, True, True, 10)
        self.main_box.pack_start(self.box, False, False, 0)

        self.add(self.main_box)
        self.show_all()


class AddressError(Gtk.Window):

    def destroy(self, button):
        self.close()

    def okay_clicked(self, button):
        window.applicate()
        self.close()

    def __init__(self):
        Gtk.Window.__init__(self, title=_("Address Error"))
        self.set_icon_from_file(_ICE_ICON)
        self.set_border_width(10)

        self.main_lab = Gtk.Label()
        self.main_lab.set_markup(_("<b>Warning: HTTP or URL Error</b>"))

        self.text_lab = Gtk.Label(
            label=_("An error with the web address has been detected.\n"
                    "This is possibly the site being down or "
                    "unavailable right now.\nContinue anyway?\n"),

            justify=Gtk.Justification.CENTER
        )

        self.text_lab.set_line_wrap(True)

        self.okay = Gtk.Button(label=_("OK"))
        self.okay.connect("clicked", self.okay_clicked)
        self.cancel = Gtk.Button(label=_("Cancel"))
        self.cancel.connect("clicked", self.destroy)
        self.box.pack_end(okay, False, False, 10)
        self.box.pack_end(cancel, False, False, 0)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.pack_start(main_lab, False, False, 10)
        self.main_box.pack_start(text_lab, False, False, 0)
        self.main_box.pack_start(box, False, False, 10)

        self.add(main_box)
        self.show_all()


class Ice(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Ice")
        self.current_directory = os.path.realpath(_APPS_DIR)

        self.set_icon_name("ice")
        self.set_border_width(5)

        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.set_titlebar(self.header)

        self.main_stack = Gtk.Stack()
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.main_stack)
        self.header.set_custom_title(self.stack_switcher)

        ######################
        #   'Create' page.   #
        ######################

        self.create_grid = Gtk.Grid()
        self.create_grid.set_column_homogeneous(True)
        self.create_grid.set_row_spacing(5)
        self.create_grid.set_column_spacing(5)

        self.welcome = Gtk.Label()
        self.welcome.set_markup(_(
            "<b>Welcome to Ice, a simple SSB manager.</b>")
        )
        self.name = Gtk.Entry()
        self.name.set_placeholder_text(_("Name the application"))
        self.url = Gtk.Entry()
        self.url.set_placeholder_text(_("Enter web address"))

        self.where_store = [_("Accessories"), _("Games"),
                            _("Graphics"), _("Internet"),
                            _("Office"), _("Programming"),
                            _("Multimedia"), _("System")]

        self.where_lab = Gtk.Label(label=_("Where in the menu?"))
        self.where = Gtk.ComboBoxText()
        self.where.set_entry_text_column(0)
        for entry in self.where_store:
            self.where.append_text(entry)
        self.where.set_active(3)

        self.iconpath = _ICE_ICON
        self.icon = Gtk.Image.new_from_icon_name("ice", 6)
        # self.icon = Gtk.Image()
        # self.icon.set_from_pixbuf(self.icon_pixbuf)

        self.choose_icon = Gtk.Button(label=_("Select an icon"))
        self.choose_icon.connect("clicked", self.icon_select)
        self.download_icon = Gtk.Button(label=_("Use site favicon"))
        self.download_icon.connect("clicked", self.thread_icon_download)

        self.isolate_profile = False
        self.isolate_button = Gtk.CheckButton()
        self.isolate_lab = Gtk.Label(label=_("Isolate the SSB"))
        self.isolate_button.add(self.isolate_lab)
        self.isolate_button.connect("toggled", self.isolate_clicked)

        self.firefox = Gtk.RadioButton.new_with_label_from_widget(None,
                                                                  "Firefox")

        if not os.path.exists(_FIREFOX_BIN):
            self.firefox.set_sensitive(False)

        if not os.path.exists(_CHROMIUM_BIN) and not \
                os.path.exists(_CHROME_BIN) and not \
                os.path.exists(_BRAVE_BIN) and not \
                os.path.exists(_EPIPHANY_BIN) and not \
                os.path.exists(_VIVALDI_BIN) and \
                os.path.exists(_FIREFOX_BIN):
            self.firefox.set_active(True)

        self.firefox.connect("clicked", self.browser_button)

        self.brave = Gtk.RadioButton.new_from_widget(self.firefox)
        self.brave.set_label("Brave")

        if not os.path.exists(_BRAVE_BIN):
            self.brave.set_sensitive(False)

        if not os.path.exists(_CHROMIUM_BIN) and not \
                os.path.exists(_FIREFOX_BIN) and not \
                os.path.exists(_CHROME_BIN) and not \
                os.path.exists(_EPIPHANY_BIN) and not \
                os.path.exists(_VIVALDI_BIN) and \
                os.path.exists(_BRAVE_BIN):
            self.brave.set_active(True)

        self.brave.connect("clicked", self.browser_button)

        self.chrome = Gtk.RadioButton.new_from_widget(self.brave)
        self.chrome.set_label("Chrome")

        if not os.path.exists(_CHROME_BIN):
            self.chrome.set_sensitive(False)

        if not os.path.exists(_CHROMIUM_BIN) and not \
                os.path.exists(_FIREFOX_BIN) and not \
                os.path.exists(_BRAVE_BIN) and not \
                os.path.exists(_EPIPHANY_BIN) and not \
                os.path.exists(_VIVALDI_BIN) and \
                os.path.exists(_CHROME_BIN):
            self.chrome.set_active(True)

        self.chrome.connect("clicked", self.browser_button)

        self.vivaldi = Gtk.RadioButton.new_from_widget(self.chrome)
        self.vivaldi.set_label("Vivaldi")

        if not os.path.exists(_VIVALDI_BIN):
            self.vivaldi.set_sensitive(False)

        if not os.path.exists(_CHROMIUM_BIN) and not \
                os.path.exists(_FIREFOX_BIN) and not \
                os.path.exists(_BRAVE_BIN) and not \
                os.path.exists(_EPIPHANY_BIN) and not \
                os.path.exists(_CHROME_BIN) and \
                os.path.exists(_VIVALDI_BIN):
            self.vivaldi.set_active(True)

        self.vivaldi.connect("clicked", self.browser_button)

        self.chromium = Gtk.RadioButton.new_from_widget(self.vivaldi)
        self.chromium.set_label("Chromium")

        if not os.path.exists(_CHROMIUM_BIN):
            self.chromium.set_sensitive(False)

        if not os.path.exists(_CHROME_BIN) and not \
                os.path.exists(_FIREFOX_BIN) and not \
                os.path.exists(_BRAVE_BIN) and not \
                os.path.exists(_EPIPHANY_BIN) and not \
                os.path.exists(_VIVALDI_BIN) and \
                os.path.exists(_CHROMIUM_BIN):
            self.chromium.set_active(True)

        self.chromium.connect("clicked", self.browser_button)

        self.epiphany = Gtk.RadioButton.new_from_widget(self.chromium)
        self.epiphany.set_label("GNOME Web")

        if not os.path.exists(_EPIPHANY_BIN):
            self.epiphany.set_sensitive(False)

        if not os.path.exists(_CHROME_BIN) and not \
                os.path.exists(_FIREFOX_BIN) and not \
                os.path.exists(_BRAVE_BIN) and not \
                os.path.exists(_VIVALDI_BIN) and not \
                os.path.exists(_CHROMIUM_BIN) and \
                os.path.exists(_EPIPHANY_BIN):
            self.epiphany.set_active(True)
        
        self.epiphany.connect("clicked", self.browser_button)

        if self.firefox.get_active() is True:
            self.isolate_button.set_label(_("Firefox is always isolated"))
            self.isolate_button.set_sensitive(False)
        elif self.epiphany.get_active() is True:
            self.isolate_button.set_label(_("GNOME Web is always isolated"))
            self.isolate_button.set_sensitive(False)

        self.apply_button = Gtk.Button(label=_("Apply"))
        self.apply_button.connect("clicked", self.thread_apply_clicked)

        self.browser_box = Gtk.FlowBox()
        self.browser_box.set_row_spacing(0)
        self.browser_box.set_column_spacing(0)
        self.browser_box.add(self.brave)
        self.browser_box.add(self.chrome)
        self.browser_box.add(self.chromium)
        self.browser_box.add(self.firefox)
        self.browser_box.add(self.vivaldi)
        self.browser_box.add(self.epiphany)
        
        self.option_box = Gtk.FlowBox()
        self.option_box.set_row_spacing(0)
        self.option_box.set_column_spacing(0)
        self.option_box.add(self.isolate_button)

        self.create_grid.attach(self.name, 1, 2, 2, 1)
        self.create_grid.attach(self.url, 1, 3, 2, 1)
        self.create_grid.attach(self.where_lab, 1, 4, 1, 1)
        self.create_grid.attach(self.where, 2, 4, 1, 1)
        self.create_grid.attach(self.icon, 1, 5, 1, 2)
        self.create_grid.attach(self.choose_icon, 2, 5, 1, 1)
        self.create_grid.attach(self.download_icon, 2, 6, 1, 1)
        self.create_grid.attach(self.browser_box, 1, 8, 2, 2)
        self.create_grid.attach(self.option_box, 1, 11, 2, 2)
        self.create_grid.attach(self.apply_button, 2, 13, 1, 1)

        self.create_lab = Gtk.Label(label=_("Create"))

        ######################
        #   'Remove' page.   #
        ######################

        self.known_profiles = []
        self.liststore = Gtk.ListStore(Pixbuf, str)

        for fl in os.listdir(_APPS_DIR):
            self.a = "{0}/{1}".format(_APPS_DIR, fl)
            if not os.path.isdir(self.a):
                self.details = self.get_details(self.a)
                if self.details is not None:
                    self.liststore.append([self.details['pixbuf'],
                                           self.details['nameline']])
                    self.known_profiles.append(self.details)

        self.clean_orphaned_profiles(self.known_profiles)

        self.iconview = Gtk.IconView()
        self.iconview.set_model(self.liststore)
        self.iconview.set_pixbuf_column(0)
        self.iconview.set_text_column(1)
        self.iconview.set_selection_mode(1)
        self.iconview.connect("item-activated", self.delete)

        self.remove_scroll = Gtk.ScrolledWindow()
        self.remove_scroll.add(self.iconview)

        self.main_stack.add_titled(self.create_grid, "create", _("Create"))
        self.main_stack.add_titled(self.remove_scroll, "remove", _("Remove"))

        self.add(self.main_stack)
        self.show_all()

        if not os.path.exists(_CHROME_BIN) and not \
                os.path.exists(_CHROMIUM_BIN) and not \
                os.path.exists(_VIVALDI_BIN) and not \
                os.path.exists(_BRAVE_BIN) and not \
                os.path.exists(_FIREFOX_BIN):
            self.apply_button.set_sensitive(False)
            ErrorDialog(
                "Browser Error",
                "Warning: No Suitable Browser Detected",
                "Ice can not detect any browsers.\n"
                "Please make sure you have a supported browser installed.",
            )

    def destroy(self, button):
        Gtk.main_quit()

    def icon_select(self, button):
        IconSel()

    def thread_apply_clicked(self, button):
        button.set_label(_("Applying"))
        applythread = threading.Thread(target=self.apply_clicked)
        applythread.daemon = True
        applythread.start()
        button.set_label(_("Apply"))

    def apply_clicked(self):
        if self.errortest(self.normalize(self.url.get_text())) is not None:
            self.applicate()
        elif self.errortest(self.normalize(self.url.get_text())) is None:
            GLib.idle_add(self.apply_errors, "address")
        else:
            GLib.idle_add(self.apply_errors, "unknown")

    def apply_errors(self, errortype):
        if errortype == "address":
            AddressError()
        elif errortype == "unknown":
            ErrorDialog(
                "Error Applying SSB",
                "Error: Unknown Error",
                "An unknown error has occurred. :(",
            )

    def isolate_clicked(self, button):
        self.isolate_profile = False
        if button.get_active() is True:
            self.isolate_profile = True

    def get_details(self, app):
        self.a = open(app, 'r', errors='ignore')
        self.nameline = ""
        self.iconline = ""
        self.profile = ""
        self.is_ice = False
        self.is_firefox = False
        self.is_isolated = False

        for line in self.a:
            if "Name=" in line:
                self.array = line.replace("=", " ").split()
                self.array.pop(0)
                for word in self.array:
                    self.nameline = self.nameline + word + " "
            elif "Icon=" in line:
                self.array = line.replace("=", " ").split()
                self.array.pop(0)
                for word in self.array:
                    self.iconline = self.iconline + word
                try:
                    self.pixbuf = Pixbuf.new_from_file_at_size(self.iconline,
                                                               16, 16)
                except GLib.Error:
                    self.pixbuf = Gtk.Image.new_from_icon_name(
                        "ice",
                        6
                    ).get_pixbuf(),
            elif "StartupWMClass=Chromium" in line:
                # for legacy apps
                self.is_ice = True
            elif "StartupWMClass=ICE-SSB" in line:
                self.is_ice = True
            elif "IceFirefox=" in line:
                self.is_firefox = True
                self.profile = str.replace(line, 'IceFirefox=', '').strip()
            elif "X-ICE-SSB-Profile=" in line:
                self.is_isolated = True
                self.profile = str.replace(line,
                                           'X-ICE-SSB-Profile=', '').strip()

        if self.nameline != "" and self.iconline != "" and self.is_ice is True:
            self.details = {
                'nameline': self.nameline,
                'profile': self.profile,
                'is_firefox': self.is_firefox,
                'is_isolated': self.is_isolated,
                'pixbuf': self.pixbuf
            }
            return self.details

        return None

    def normalize(self, url):
        (self.scheme, self.netloc,
         self.path, _, _, _) = urllib.parse.urlparse(url, "http")

        if not self.netloc and self.path:
            return urllib.parse.urlunparse((self.scheme,
                                            self.path, "", "", "", ""))

        return urllib.parse.urlunparse((self.scheme, self.netloc,
                                        self.path, "", "", ""))

    def errortest(self, url):
        try:
            return urllib.request.urlopen(url, timeout=3)
        except (urllib.request.HTTPError, urllib.request.URLError):
            return None

    def thread_icon_download(self, button):
        self.download_icon.set_label(_("Downloading favicon"))
        iconthread = threading.Thread(target=self.icon_download)
        iconthread.daemon = True
        iconthread.start()

    def icon_download(self):
        self.appurl = self.normalize(self.url.get_text())
        self.parsed_uri = urllib.parse.urlparse(self.appurl)
        self.iconformats = ["apple-touch-icon", "shortcut icon",
                            "icon", "msapplication-TileImage"]
        self.icon_link = None
        self.page = self.errortest(self.appurl)

        if self.page is not None:
            self.soup = bs4.BeautifulSoup(self.page.read(), "html.parser")

            og_image = self.soup.find("meta", {"property": "og:image"})
            if og_image is not None:
                og_image = og_image["content"]
                if ("://") in og_image:
                    self.icon_link = og_image
                else:
                    self.icon_link = (self.parsed_uri.scheme + "://" +
                                      self.parsed_uri.netloc +
                                      og_image["content"])
            else:
                for iconformat in self.iconformats:
                    self.icon_link = self.soup.find("link", {"rel": iconformat})
                    if self.icon_link is not None:
                        self.icon_link = (self.parsed_uri.scheme + "://" +
                                          self.parsed_uri.netloc +
                                          self.icon_link["href"])

            if self.icon_link is None:
                self.iconrequest = requests.get(
                    self.parsed_uri.scheme + "://" +
                    self.parsed_uri.netloc + "/favicon.ico"
                )

                try:
                    if self.iconrequest.status_code == 200:
                        self.icon_link = (
                            self.parsed_uri.scheme + "://" +
                            self.parsed_uri.netloc + "/favicon.ico"
                        )
                except ConnectionError:
                    pass

            if self.icon_link is None:
                self.iconrequest = requests.get(
                    'https://www.google.com/s2/favicons?domain=' + self.appurl
                )
                try:
                    if self.iconrequest.status_code == 200:
                        self.icon_link = (
                            self.parsed_uri.scheme + "://" +
                            self.parsed_uri.netloc + "/favicon.ico"
                        )
                except ConnectionError:
                    pass

            # Catches ValueError (if the Favicon detector gets an invalid URL)
            try:
                self.icondl = urllib.request.urlopen(self.icon_link)
                self.icon_name = self.icon_link.replace("/", " ").split()[-1]
                self.icon_ext = self.icon_name.replace(".", " ").split()[-1]
                with open(_ICON_DIR + "/favicon." + self.icon_ext, "wb") as f:
                    f.write(self.icondl.read())
                self.iconpath = _ICON_DIR + "/favicon." + self.icon_ext
            except ValueError:
                GLib.idle_add(self.apply_icon, None)
            else:
                GLib.idle_add(self.apply_icon, True)

        elif self.page is None:
            GLib.idle_add(self.apply_icon, False)
        else:
            GLib.idle_add(self.apply_icon, None)

    def apply_icon(self, done):
        if done is True:
            self.new_icon = Pixbuf.new_from_file_at_size(
                _ICON_DIR + "/favicon." + self.icon_ext, 32, 32
            )
            self.icon.set_from_pixbuf(self.new_icon)
        elif done is False:
            ErrorDialog(
                "Address Error",
                "Error: HTTP or URL Error",
                "An error with the web address has been detected.\n"
                "This is possibly the site being down or"
                " unavailable right now.\n"
                "Please check the URL",
            )
            self.iconpath = _ICE_ICON
            self.new_icon = Pixbuf.new_from_file_at_size(_ICE_ICON, 32, 32)
            self.icon.set_from_pixbuf(self.new_icon)
        else:
            ErrorDialog(
                "Error Applying SSB",
                "Error: Unknown Error",
                "An unknown error has occurred. :(",
            )
            self.iconpath = _ICE_ICON
            self.new_icon = Pixbuf.new_from_file_at_size(_ICE_ICON, 32, 32)
            self.icon.set_from_pixbuf(self.new_icon)
        self.download_icon.set_label(_("Use site favicon"))
        return False

    def applicate(self):
        self.title = self.name.get_text()
        self.address = self.normalize(self.url.get_text())

        self.semiformatted = ""
        self.array = filter(str.isalpha, self.title)
        for obj in self.array:
            self.semiformatted = self.semiformatted + obj
        self.formatted = self.semiformatted.lower()

        self.loc = self.where.get_active_text()
        if self.loc == _("Accessories"):
            self.location = "Utility;"
        elif self.loc == _("Games"):
            self.location = "Game;"
        elif self.loc == _("Graphics"):
            self.location = "Graphics;"
        elif self.loc == _("Internet"):
            self.location = "Network;"
        elif self.loc == _("Office"):
            self.location = "Office;"
        elif self.loc == _("Programming"):
            self.location = "Development;"
        elif self.loc == _("Multimedia"):
            self.location = "AudioVideo;"
        elif self.loc == _("System"):
            self.location = "System;"

        self.iconname = self.iconpath.replace("/", " ").split()[-1]
        self.iconext = self.iconname.replace(".", " ").split()[-1]

        if os.path.exists("{0}/{1}.desktop".format(_APPS_DIR, self.formatted)):
            GLib.idle_add(self.applicate_error, "Duplicate")
        elif len(self.title) == 0:
            GLib.idle_add(self.applicate_error, "Name")
        else:
            self.writefile(self.title, self.formatted, self.address,
                           self.iconext, self.location)

    def writefile(self, title, formatted, address, iconext, location):
        shutil.copyfile(self.iconpath,
                        "{0}/{1}.{2}".format(_ICON_DIR, formatted, iconext))
        self.appfile = os.path.expanduser("{0}/{1}.desktop".format(_APPS_DIR,
                                                                   formatted))
        if self.chrome.get_active() is True:
            self.browser = "google-chrome"
        elif self.chromium.get_active() is True:
            self.browser = "chromium-browser"
        elif self.brave.get_active() is True:
            self.browser = "brave"
        elif self.vivaldi.get_active() is True:
            self.browser = "vivaldi"
        elif self.firefox.get_active() is True:
            self.browser = "firefox"
        elif self.epiphany.get_active() is True:
            self.browser = "epiphany"
        else:
            print(_("ERROR: An unknown browser selection error has occurred."))
            sys.exit(1)

        with open(self.appfile, 'w') as self.appfile1:
            self.appfile1.truncate()

            self.appfile1.write("[Desktop Entry]\n")
            self.appfile1.write("Version=1.0\n")
            self.appfile1.write("Name={0}\n".format(title))
            self.appfile1.write("Comment={0} (Ice SSB)\n".format(title))

            if self.browser == "firefox":
                self.firefox_profile_path = "{0}/{1}".format(_FF_PROFILES_DIR,
                                                             formatted)
                self.appfile1.write("Exec=" + self.browser +
                                    " --class ICE-SSB-" + formatted +
                                    " --profile " + self.firefox_profile_path +
                                    " --no-remote " + address + "\n")

                self.appfile1.write("IceFirefox={0}\n".format(formatted))
                self.init_firefox_profile(self.firefox_profile_path)
            elif self.browser == "epiphany":
                self.epiphany_profile_path = "{0}/{1}".format(
                    _EPIPHANY_PROFILES_DIR, "epiphany-" + formatted
                )
                self.appfile1.write(
                    "Exec={0} --application-mode --profile=\""
                    "{2}\" {1}\n".format(
                        self.browser, address, self.epiphany_profile_path
                    )
                )
                self.appfile1.write("IceEpiphany={0}\n".format(formatted))
            else:
                if self.isolate_profile is True:
                    self.profile_path = "{0}/{1}".format(_PROFILES_DIR,
                                                         formatted)
                    self.appfile1.write("Exec=" + self.browser +
                                        " --app=" + address +
                                        " --class=ICE-SSB-" + formatted +
                                        " --user-data-dir=" +
                                        self.profile_path + "\n")

                    self.appfile1.write("X-ICE-SSB-Profile=" +
                                        formatted + "\n")
                else:
                    self.appfile1.write("Exec=" + self.browser +
                                        " --app=" + address +
                                        " --class=ICE-SSB-" + formatted +
                                        "\n")

            self.appfile1.write("Terminal=false\n")
            self.appfile1.write("X-MultipleArgs=false\n")
            self.appfile1.write("Type=Application\n")
            if self.browser == "epiphany":
                self.appfile1.write("Icon={0}/app-icon.{2}\n".format(
                    self.epiphany_profile_path,
                    formatted,
                    iconext
                ))
            else:
                self.appfile1.write("Icon={0}/{1}.{2}\n".format(
                    _ICON_DIR,
                    formatted,
                    iconext
                ))

            self.appfile1.write("Categories=GTK;{0}\n".format(location))
            self.appfile1.write("MimeType=text/html;text/xml;"
                                "application/xhtml_xml;\n")

            self.appfile1.write(
                "StartupWMClass=ICE-SSB-{0}\n".format(formatted)
            )
            self.appfile1.write("StartupNotify=true\n")

            if self.browser == "epiphany":
                self.init_epiphany_profile(
                    self.epiphany_profile_path,
                    formatted, iconext, self.appfile
                )

        GLib.idle_add(self.ice_update)

    def ice_update(self):
        self.name.set_text("")
        self.url.set_text("")
        self.iconpath = _ICE_ICON
        self.new_icon = Pixbuf.new_from_file_at_size(self.iconpath, 32, 32)
        self.icon.set_from_pixbuf(self.new_icon)
        self.details = self.get_details(self.appfile)
        if self.details is not None:
            self.liststore.prepend([self.details['pixbuf'],
                                    self.details['nameline']])

    def init_firefox_profile(self, path):
        self.chromepath = "{0}/chrome".format(path)
        self.settingsfile = "{0}/user.js".format(path)
        self.cssfile = "{0}/userChrome.css".format(self.chromepath)

        os.makedirs(self.chromepath)

        try:
            shutil.copyfile('/usr/lib/peppermint/ice/search.json.mozlz4',
                            path + '/search.json.mozlz4')
        except FileNotFoundError:
            print("Error: search.json.mozlz4 not found")

        try:
            shutil.copyfile('/usr/lib/peppermint/ice/places.sqlite',
                            path + '/places.sqlite')
        except FileNotFoundError:
            print("Error: places.sqlite not found")

        with open(self.cssfile, 'w') as cfile:
            cfile.write("#nav-bar, #identity-box, #tabbrowser-tabs, "
                        "#TabsToolbar { visibility: collapse !important; }")

        with open(self.settingsfile, 'w') as sfile:
            sfile.write('user_pref("browser.cache.disk.enable",'
                        ' false);')
            sfile.write('user_pref("browser.cache.disk.capacity", 0);')
            sfile.write('user_pref("browser.cache.disk.filesystem_reported"'
                        ', 1);')
            sfile.write('user_pref("browser.cache.disk.smart_size.enabled",'
                        ' false);')
            sfile.write('user_pref("browser.cache.disk.smart_size.first_run",'
                        ' false);')
            sfile.write('user_pref("browser.cache.disk.smart_size.use_old_max"'
                        ', false);')
            sfile.write('user_pref("browser.ctrlTab.previews", true);')
            sfile.write('user_pref("browser.tabs.drawInTitlebar", false);')
            sfile.write('user_pref("browser.tabs.warnOnClose", false);')
            sfile.write('user_pref("browser.toolbars.bookmarks.visibility"'
                        ', false);')
            sfile.write('user_pref("plugin.state.flash", 2);')
            sfile.write('user_pref("toolkit.legacyUserProfileCustomizations.'
                        'stylesheets", true);')

    def init_epiphany_profile(self, path, formatted, iconext, appfile):
        os.makedirs(path)
        shutil.copyfile("{0}/{1}.{2}".format(_ICON_DIR, formatted, iconext),
                        "{0}/app-icon.{1}".format(path, iconext))
        # subprocess.run(["touch", path + "/.app"])
        os.replace(appfile, "{0}/epiphany-{1}.desktop".format(path, formatted))
        os.symlink("{0}/epiphany-{1}.desktop".format(path, formatted), appfile)

    def delete(self, button, item):
        self.a = self.iconview.get_selected_items()
        self.b = self.liststore.get_iter(self.a[0])
        self.c = self.liststore.get_value(self.b, 1)
        self.liststore.remove(self.b)

        self.semiformatted = ""
        self.array = filter(str.isalpha, self.c)

        for obj in self.array:
            self.semiformatted = self.semiformatted + obj

        self.formatted = self.semiformatted.lower()
        self.appfile = "{0}/{1}.desktop".format(_APPS_DIR, self.formatted)

        self.appfileopen = open(self.appfile, 'r')
        self.appfilelines = self.appfileopen.readlines()
        self.appfileopen.close()

        for line in self.appfilelines:
            if "IceFirefox=" in line:
                self.profile = line.replace('IceFirefox=', '')
                self.profile = self.profile.rstrip('\n')
                shutil.rmtree("{0}/{1}".format(_FF_PROFILES_DIR, self.profile))

            if "IceEpiphany=" in line:
                self.profile = str.replace(line, 'IceEpiphany=', '')
                self.profile = str.replace(self.profile, "\n", '')
                shutil.rmtree("{0}/epiphany-{1}".format(_EPIPHANY_PROFILES_DIR,
                                                        self.profile))

            if "X-ICE-SSB-Profile=" in line:
                self.profile = line.replace('X-ICE-SSB-Profile=', '')
                self.profile = self.profile.rstrip('\n')
                shutil.rmtree("{0}/{1}".format(_PROFILES_DIR, self.profile))

        os.remove(self.appfile)

    def applicate_error(self, error):
        if error == "Duplicate":
            ErrorDialog(
                "Duplication Error",
                "Warning: File Duplication Error",
                "The name of the SSB matches the name of an another SSB.\n"
                "Please remove the duplicate SSB\n or change the SSB name.",
            )
        if error == "Name":
            ErrorDialog(
                "Empty Name Error",
                "Error: No Application Name Entered.",
                "Please enter an application name to continue.",
            )

    def clean_orphaned_profiles(self, known_apps):
        self.known_profiles = []
        for app in known_apps:
            self.a = "{0}/{1}".format(_FF_PROFILES_DIR, app['profile'])
            if app['profile'] != "":
                # make sure firefox apps have profiles available
                if app['is_firefox'] is True and not os.path.isdir(self.a):
                    self.init_firefox_profile(self.a)
                self.known_profiles.append(app['profile'])

        for p_type in ['profiles', 'firefox']:
            for fl in os.listdir("{0}/{1}/".format(_ICE_DIR, p_type)):
                self.a = "{0}/{1}/{2}".format(_ICE_DIR, p_type, fl)
                if not os.path.isdir(self.a) or fl not in self.known_profiles:
                    shutil.rmtree(self.a)

    def browser_button(self, button):
        if button.get_label() == "Firefox":
            self.isolate_button.set_label(_("Firefox is always Isolated"))
            self.isolate_button.set_sensitive(False)
        elif button.get_label() == "GNOME Web":
            self.isolate_button.set_label(_("GNOME Web is always Isolated"))
            self.isolate_button.set_sensitive(False)
        else:
            self.isolate_button.set_label(_("Isolate the SSB"))
            self.isolate_button.set_sensitive(True)


if __name__ == '__main__':
    window = Ice()
    window.connect("delete-event", Gtk.main_quit)
    Gtk.main()
