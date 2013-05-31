#!/usr/bin/env python

#  
#  Copyright (C) 2010 Tom Cowell, Rico Tzschichholz, Robert Dyer
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
import dbus
import dbus.glib
import sys
import os

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	print e
	exit()

emesenebus = "org.emesene.dbus"
emesenepath = "/org/emesene/dbus"
emeseneiface = "org.emesene.dbus"

class EmeseneItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.emesene = None

		self.bus.add_signal_receiver(self.name_owner_changed_cb, dbus_interface='org.freedesktop.DBus', signal_name = 'NameOwnerChanged')
		obj = self.bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")

		self.bus_interface.ListNames (reply_handler=self.list_names_handler, error_handler=self.list_names_error_handler)

		self.bus.add_signal_receiver(self.conversation_updated, "unread_messages", emeseneiface, emesenebus, emesenepath)
	
	def list_names_handler(self, names):
		if emesenebus in names:
			self.init_emesene_objects()
			self.update_badge()

	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)

	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == emesenebus:
			if new_owner:
				self.init_emesene_objects()
			else:
				self.emesene = None
				self.update_badge()

	def init_emesene_objects(self):
		obj = self.bus.get_object(emesenebus, emesenepath)
		self.emesene = dbus.Interface(obj, emeseneiface)

	def conversation_updated(self, count):
		self.update_badge()

	def update_badge(self):
		if not self.emesene:
			self.reset_badge()
			return False

		count = self.emesene.get_message_count()
		if count > 0:
			self.set_badge("%s" % count)
		else:
			self.reset_badge()

		return True		

class EmeseneSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("emesene.desktop"):
			self.items[pathtoitem] = EmeseneItem(self, pathtoitem)

emesenesink = EmeseneSink()

def cleanup():
	emesenesink.dispose()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)
	
	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))
	
	mainloop.run()
