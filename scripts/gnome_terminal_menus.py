#!/usr/bin/env python

#
# Copyright (C) 2010 Felipe Morales
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
import gconf
from subprocess import Popen
import gobject, atexit, sys
from signal import signal, SIGTERM

class DockManagerTerminalProfileItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)

		for profile in sink.profiles:
			self.add_profile_menuitem(profile)

	def add_profile_menuitem(self, profilename):
		self.add_menu_item(profilename, "gnome-terminal", "Profiles")
	
	def menu_pressed(self, menu_id):
		profile_name = self.id_map[menu_id]
		pid = Popen(["gnome-terminal", "--window-with-profile=" + profile_name]).pid

class DockManagerTerminalSink(DockManagerSink):
	def __init__(self):
		self.profiles = []
		self.get_profiles()
		DockManagerSink.__init__(self)

	def get_profiles(self):
		gc = gconf.Client()
		profiles = gc.all_dirs("/apps/gnome-terminal/profiles")
		for profile in profiles:
			visible_name = gc.get_string(profile + "/visible_name")
			self.profiles.append(visible_name)

	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith(("gnome-terminal.desktop")):
			self.items[pathtoitem] = DockManagerTerminalProfileItem(self, pathtoitem)

sink = DockManagerTerminalSink()

def cleanup():
	sink.dispose()

if __name__ == "__main__":
	mainloop = gobject.MainLoop()

	atexit.register(cleanup)
	signal(SIGTERM, lambda signum, stacj_frame: sys.exit(1))

	mainloop.run()
