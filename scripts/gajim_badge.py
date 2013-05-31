#!/usr/bin/env python

#  
#  Copyright (C) 2010 Rico Tzschichholz, Stefan Bethge, Robert Dyer
#
#  Started from liferea_badge.py
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
import dbus
import dbus.glib
import glib
import sys
import os

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	print e
	exit()

gajimbus = "org.gajim.dbus"
gajimpath = "/org/gajim/dbus/RemoteObject"
gajimiface = "org.gajim.dbus.RemoteInterface"
	
class GajimItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.timer = 0
		self.gajim = None
		
		self.bus.add_signal_receiver(self.name_owner_changed_cb,
				dbus_interface='org.freedesktop.DBus',
				signal_name='NameOwnerChanged')
		
		obj = self.bus.get_object ("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		
		self.bus_interface.ListNames (reply_handler=self.list_names_handler, error_handler=self.list_names_error_handler)

		self.bus.add_signal_receiver(self.signal_new_message, "NewMessage", gajimiface, gajimbus, gajimpath)

	def list_names_handler(self, names):
		if gajimbus in names:
			self.init_gajim_objects()
			self.update_badge()

	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == gajimbus:
			if new_owner:
				self.init_gajim_objects()
			else:
				self.gajim = None
				if self.timer > 0:
					gobject.source_remove (self.timer)
					self.timer = 0
				self.update_badge()
	
	def init_gajim_objects(self):
		obj = self.bus.get_object(gajimbus, gajimpath)
		self.gajim = dbus.Interface(obj, gajimiface)

		if not self.timer > 0:
			self.timer = gobject.timeout_add (5000, self.update_badge)

	def signal_new_message(self, details):
		self.update_badge()

	def update_badge(self):
		if not self.gajim:
			self.reset_badge()
			return False
		
		items_unread = self.gajim.get_unread_msgs_number()

		if int(items_unread) > 0:
			self.set_badge("%s" % items_unread)
		else:
			self.reset_badge()
		return True

class GajimSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("gajim.desktop"):
			self.items[pathtoitem] = GajimItem(self, pathtoitem)

gajimsink = GajimSink()

def cleanup ():
	gajimsink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	mainloop.run()
