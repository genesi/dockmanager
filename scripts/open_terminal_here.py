#!/usr/bin/env python

#  
#  Copyright (C) 2009 Jason Smith, Robert Dyer
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
import gconf
import gobject
import glib
import sys
import urllib
import os

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	exit()

class TerminalItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		
		client = gconf.client_get_default()
		self.terminal = client.get_string("/desktop/gnome/applications/terminal/exec")
		if self.terminal == None:
			self.terminal = "gnome-terminal"
		
		self.path = urllib.unquote(str(self.iface.Get(DOCKITEM_IFACE, "Uri", dbus_interface="org.freedesktop.DBus.Properties")[7:]))
		if not os.path.isdir (self.path):
			self.path = os.path.dirname (self.path)
		
		self.add_menu_item("Open Terminal Here", "terminal", "actions")

	def menu_pressed(self, menu_id):
		if self.id_map[menu_id] == "Open Terminal Here":
			oldDir = os.getcwd()
			os.chdir(self.path)
			os.system ('%s &' % self.terminal)
			os.chdir(oldDir)
			
class TerminalSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "Uri", dbus_interface="org.freedesktop.DBus.Properties").startswith ("file://"):
			self.items[pathtoitem] = TerminalItem(self, pathtoitem)

terminalsink = TerminalSink()

def cleanup ():
	terminalsink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	mainloop.run()
