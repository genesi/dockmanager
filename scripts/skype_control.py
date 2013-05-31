#!/usr/bin/env python

#  
#  Copyright (C) 2010 Lukasz Marcinowski, Rico Tzschichholz
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
import time
import dbus.service

import time

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink
	from dockmanager.dockmanager import RESOURCESDIR, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	exit()

skypebus = "com.Skype.API"
skypepath = "/com/Skype"
skypeclientpath = "/com/Skype/Client"
skypeclientitem = "com.Skype.API.Client"
skypeitem = "com.Skype.API"

STATUS_ICON_OFFLINE = os.path.join(RESOURCESDIR, "skype_offline.svg")
STATUS_ICON_ONLINE = os.path.join(RESOURCESDIR, "skype_online.svg")
STATUS_ICON_AWAY = os.path.join(RESOURCESDIR, "skype_away.svg")
STATUS_ICON_SKYPEME = os.path.join(RESOURCESDIR, "skype_skypeme.svg")
STATUS_ICON_DND = os.path.join(RESOURCESDIR, "skype_dnd.svg")
STATUS_ICON_NA = os.path.join(RESOURCESDIR, "skype_na.svg")
STATUS_ICON_INVISIBLE = os.path.join(RESOURCESDIR, "skype_invisible.svg")


class SkypeNotify(dbus.service.Object):
	def __init__(self, bus, notify):
		dbus.service.Object.__init__(self, dbus.SessionBus(), skypeclientpath)
		self.notify = notify
	
	@dbus.service.method(dbus_interface=skypeclientitem)	
	def Notify(self, com):
		self.notify(unicode(com))

class DockySkypeItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.items_unread = 0
		self.skype = None
		self.skype_in = SkypeNotify(self.bus, self.notify_cb)

		self.owner_changed_signal = self.bus.add_signal_receiver(
					handler_function = self.name_owner_changed_cb,
					dbus_interface = 'org.freedesktop.DBus', 
					signal_name = 'NameOwnerChanged')
		
		obj = self.bus.get_object ("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		self.bus_interface.ListNames (reply_handler = self.list_names_handler, 
					      error_handler = self.list_names_error_handler)
	
	def dispose(self):
		if self.skype_in:
			self.skype_in.remove_from_connection()
			self.skype_in = None
		self.owner_changed_signal.remove()

	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	def list_names_handler(self, names):
		if skypebus in names:
			self.init_skype_objects()
		else:
			self.items_unread = 0
			self.skype = None
		self.set_menu_buttons()
		self.update_badge()
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == skypebus:
			if new_owner:
				self.init_skype_objects()
			else:
				self.items_unread = 0
				self.skype = None
			self.set_menu_buttons()
			self.update_badge()
	
	def init_skype_objects(self):
		obj = self.bus.get_object (skypebus, skypepath)
		self.skype = dbus.Interface (obj, skypeitem)
		while self.skype.Invoke("NAME dockmanager_helper") == "CONNSTATUS OFFLINE":
			time.sleep(1)
		self.skype.Invoke("PROTOCOL 5")
	
	def clear_menu_buttons(self):
		for k in self.id_map.keys():
			self.remove_menu_item(k)
	
	def set_menu_buttons(self):
		self.clear_menu_buttons()
		if not self.skype:
			return
		
		self.add_menu_item("Show/Hide", "skype", "Skype")
		self.add_menu_item("1. Online", STATUS_ICON_ONLINE, "Status")
		self.add_menu_item("2. Away", STATUS_ICON_AWAY, "Status")
		self.add_menu_item("3. DND", STATUS_ICON_DND, "Status")
		self.add_menu_item("4. NA", STATUS_ICON_NA, "Status")
		self.add_menu_item("5. Skypeme", STATUS_ICON_SKYPEME, "Status")
		self.add_menu_item("6. Invisible", STATUS_ICON_INVISIBLE, "Status")
		self.add_menu_item("7. Offline", STATUS_ICON_OFFLINE, "Status")
	
	def menu_pressed(self, menu_id):
		if not self.skype:
			return
		
		menu_id = self.id_map[menu_id]
		
		if menu_id == "Show/Hide":
			self.show_hide()
		elif menu_id == "2. Away":
			self.skype.Invoke("SET USERSTATUS AWAY")
		elif menu_id == "1. Online":
			self.skype.Invoke("SET USERSTATUS Online")
		elif menu_id == "5. Skypeme":
			self.skype.Invoke("SET USERSTATUS SKYPEME")
		elif menu_id == "7. Offline":
			self.skype.Invoke("SET USERSTATUS OFFLINE")
		elif menu_id == "3. DND":
			self.skype.Invoke("SET USERSTATUS DND")
		elif menu_id == "4. NA":
			self.skype.Invoke("SET USERSTATUS NA")
		elif menu_id == "6. Invisible":
			self.skype.Invoke("SET USERSTATUS INVISIBLE")
		elif menu_id == "8. Options":
			self.skype.Invoke("OPEN OPTIONS general")
	
	def update_badge(self):
		if not self.skype:
			self.reset_badge()
			return
		
		if int(self.items_unread) > 0:
			self.set_badge('%s' % self.items_unread)
			self.set_tooltip('Skype - %s messages/calls' % self.items_unread)
		else:
			self.reset_tooltip()
			self.reset_badge()
			self.items_unread = 0
	
	def show_hide(self):
		state = self.skype.Invoke("GET WINDOWSTATE")
		if state == "WINDOWSTATE NORMAL":
			self.skype.Invoke("SET WINDOWSTATE HIDDEN")
		elif state == "WINDOWSTATE HIDDEN":
			self.skype.Invoke("SET WINDOWSTATE NORMAL")
	
	def check_status(self):
		if not self.skype:
			return
		notify(self.skype.Invoke("GET USERSTATUS"))
	
	def notify_cb(self, cmd):
		p = cmd.split()
		if (p[0] == "CALL"):
			if (p[2] == "STATUS"):
				if p[3] == "RINGING":
					self.set_attention()
				elif p[3] == "MISSED":
					self.items_unread = self.items_unread + 1
					self.update_badge()
			elif (p[2] == "SEEN") and (p[3] =="TRUE"):
				self.items_unread = self.items_unread - 1
				self.update_badge()
		elif p[0] == "CHATMESSAGE":
			if p[3] == "RECEIVED":
				self.set_attention()
				self.items_unread = self.items_unread + 1
				self.update_badge()
			elif p[3] == "READ":
				self.items_unread = self.items_unread - 1
				self.update_badge()
		elif p[0] == "USERSTATUS":
			if p[1] == "ONLINE":
				self.set_icon(STATUS_ICON_ONLINE)
			elif p[1] == "AWAY":
				self.set_icon(STATUS_ICON_AWAY)
			elif p[1] == "SKYPEME":
				self.set_icon(STATUS_ICON_SKYPEME)
			elif p[1] == "OFFLINE":
				self.set_icon(STATUS_ICON_OFFLINE)
			elif p[1] == "DND":
				self.set_icon(STATUS_ICON_DND)
			elif p[1] == "NA":
				self.set_icon(STATUS_ICON_NA)
			elif p[1] == "INVISIBLE":
				self.set_icon(STATUS_ICON_INVISIBLE)
		elif p[0] == "CONNSTATUS":
			if p[1] == "OFFLINE":
				self.set_icon(STATUS_ICON_OFFLINE)
			elif p[1] == "CONNECTING":
				self.set_waiting()
			else:
				self.unset_waiting()


class DockySkypeSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("skype.desktop"):
			self.items[pathtoitem] = DockySkypeItem(self, pathtoitem)

dockysink = DockySkypeSink()

def cleanup ():
	dockysink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)
	
	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))
	
	mainloop.run()
