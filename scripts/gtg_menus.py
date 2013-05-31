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

#  Notes:
#  * Getting Things GNOME! 0.2 or higher is required for dbus support

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
	exit()

gtgbus = "org.GTG"
gtgpath = "/org/GTG"
gtgiface = "org.GTG"

class GTGItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.gtg = None
		
		self.bus.add_signal_receiver(self.name_owner_changed_cb,
                                             dbus_interface='org.freedesktop.DBus',
                                             signal_name='NameOwnerChanged')
                                             
		obj = self.bus.get_object ("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		
		self.bus_interface.ListNames (reply_handler=self.list_names_handler, error_handler=self.list_names_error_handler)
	
	def list_names_handler(self, names):
		if gtgbus in names:
			self.init_gtg_objects()
			self.set_menu_buttons()

	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == gtgbus:
			if new_owner:
				self.init_gtg_objects()
			else:
				self.gtg = None
			self.set_menu_buttons()
	
	def init_gtg_objects(self):
		obj = self.bus.get_object(gtgbus, gtgpath)
		self.gtg = dbus.Interface(obj, gtgiface)
		
	def clear_menu_buttons(self):
		for k in self.id_map.keys():
			self.remove_menu_item(k)
	
	def set_menu_buttons(self):
		self.clear_menu_buttons()
		
		if not self.gtg:
			return

		self.add_menu_item ("New Task", "list-add", "Task Controls")
		self.add_menu_item ("Open Tasks List", "gtg", "Task Controls")

	def menu_pressed(self, menu_id):
		if not menu_id in self.id_map:
			return	
		
		menu_id = self.id_map[menu_id]
		
		if menu_id == "New Task":
			self.gtg.open_new_task()
		elif menu_id == "Open Tasks List":
			self.gtg.show_task_browser()
		
		
class GTGSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("gtg.desktop"):
			self.items[pathtoitem] = GTGItem(self, pathtoitem)


gtgsink = GTGSink()

def cleanup ():
	gtgsink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	mainloop.run()
