#!/usr/bin/env python

#  
#  Copyright (C) 2010 James Hewitt, Robert Dyer
# 
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import atexit
import gobject
import glib
import sys
import os

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
	from subprocess import Popen
except ImportError, e:
	exit()

monitor_with_inotify = True
try:
	import pyinotify
except ImportError, e:
	print "pyinotify not available - not monitoring for new configurations"
	monitor_with_inotify = False

rdp_bookmark_dir = os.path.expanduser("~/.tsclient") 

class TsclientItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.file_map = {}
		self.read_files()

		if monitor_with_inotify:
			wm = pyinotify.WatchManager()
			handler = TsclientMonitor(item=self)
			notifier = GobjectNotifier(wm, default_proc_fun=handler)
			wm.add_watch(rdp_bookmark_dir, pyinotify.ALL_EVENTS)

	def read_files(self):
		files = os.listdir(rdp_bookmark_dir)
		for filename in files:
			self.add_file(filename)

	def add_file(self, name):
		if name[-4:] == ".rdp":
			self.file_map[name] = self.add_menu_item(name[:-4], "tsclient", "Bookmarks")

	def remove_file(self, name):
		if name[-4:] == ".rdp":
			self.remove_menu_item(self.file_map[name])
			del self.file_map[name]

	def menu_pressed(self, menu_id):
		if self.id_map[menu_id] != None:
			filename = os.path.join(rdp_bookmark_dir, self.id_map[menu_id])
			if os.path.isfile(filename):
				self.start_tsclient(filename)

	def start_tsclient(self, filename):
		Popen(["tsclient", "-x", filename])

if monitor_with_inotify:
	class GobjectNotifier(pyinotify.Notifier):
		"""
		This notifier uses a gobject io watch to trigger event processing.

		"""
		def __init__(self, watch_manager, default_proc_fun=None, read_freq=0, threshold=0, timeout=None):
			"""
			Initializes the gobject notifier. See the
			Notifier class for the meaning of the parameters.

			"""
			pyinotify.Notifier.__init__(self, watch_manager, default_proc_fun, read_freq, threshold, timeout)
			gobject.io_add_watch(self._fd, gobject.IO_IN|gobject.IO_PRI, self.handle_read)

		def handle_read(self, source, condition):
			"""
			When gobject tells us we can read from the fd, we proceed processing
			events. This method can be overridden for handling a notification
			differently.

			"""
			self.read_events()
			self.process_events()
			return True

	class TsclientMonitor(pyinotify.ProcessEvent):
		def my_init(self, item):
			self._item = item

		def process_IN_CREATE(self, event):
			self._item.add_file(event.name)

		def process_IN_DELETE(self, event):
			self._item.remove_file(event.name)

		def process_IN_MOVED_FROM(self, event):
			self._item.remove_file(event.name)

		def process_IN_MOVED_TO(self, event):
			self._item.add_file(event.name)

class TsclientSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith("tsclient.desktop"):
			self.items[pathtoitem] = TsclientItem(self, pathtoitem)

tscsink = TsclientSink()

def cleanup():
	tscsink.dispose()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register(cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	mainloop.run()
