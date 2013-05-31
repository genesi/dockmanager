#!/usr/bin/env python

#  
#  Copyright (C) 2010 Rico Tzschichholz, Robert Dyer
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

lifereabus = "org.gnome.feed.Reader"
readerpath = "/org/gnome/feed/Reader"
readeriface = "org.gnome.feed.Reader"
	
class LifereaItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.timer = 0
		self.reader = None
				
		self.bus.add_signal_receiver(self.name_owner_changed_cb,
                                             dbus_interface='org.freedesktop.DBus',
                                             signal_name='NameOwnerChanged')
                                             
		obj = self.bus.get_object ("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		
		self.bus_interface.ListNames (reply_handler=self.list_names_handler, error_handler=self.list_names_error_handler)

	def list_names_handler(self, names):
		if lifereabus in names:
			self.init_liferea_objects()
			self.update_badge()

	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == lifereabus:
			if new_owner:
				self.init_liferea_objects()
			else:
				self.reader = None
				if self.timer > 0:
					gobject.source_remove (self.timer)
					self.timer = 0
				self.update_badge()
	
	def init_liferea_objects(self):
		obj = self.bus.get_object(lifereabus, readerpath)
		self.reader = dbus.Interface(obj, readeriface)
		
		if not self.timer > 0:
			self.timer = gobject.timeout_add (10000, self.update_badge)

	def update_badge(self):
		if not self.reader:
			self.reset_badge()
			return False
		
		items_unread = self.reader.GetUnreadItems()
		#items_new = self.reader.GetNewItems()
		if items_unread > 0:
			self.set_badge("%s" % items_unread)
		else:
			self.reset_badge()
			
		return True

class LifereaSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("liferea.desktop"):
			self.items[pathtoitem] = LifereaItem(self, pathtoitem)

lifereasink = LifereaSink()

def cleanup ():
	lifereasink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	mainloop.run()
