#!/usr/bin/env python

#  
#  Copyright (C) 2010 Mike Nestor <mike@kineticoding.com>
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
import glib
import sys
import os
import time
import webbrowser
	
try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from dockmanager.dockmanager import RESOURCESDIR
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	exit()

STATUS_ICON_LOVE = "stock_about"
STATUS_ICON_BAN = "gtk-cancel"
STATUS_ICON_TIRED = "gtk-jump-to-ltr"
STATUS_ICON_URL = "gtk-dnd"
STATUS_ICON_NEXT = "stock_media-next"
STATUS_ICON_PLAY = "stock_media-play"
STATUS_ICON_PAUSE = "stock_media-pause" 

TEXT_PLAY = "Play"
TEXT_PAUSE = "Pause"
TEXT_TIRED = "Tired (30 Days)"
TEXT_BAN = "Ban (Forever)"
TEXT_LOVE = "Love"
TEXT_NEXT = "Next"
TEXT_URL = "Song Info"

DOCKY_NAME = "Pithos Control"

DBUS_BUS = "net.kevinmehall.Pithos"
DBUS_OBJECT_PATH = "/net/kevinmehall/Pithos"

class DockyPithosItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.menu_items_count = 0
		self.pithos = None
		self.song_info = None
		self.song_url = None

		self.owner_changed_signal = self.bus.add_signal_receiver(
					handler_function = self.name_owner_changed_cb,
					dbus_interface = 'org.freedesktop.DBus', 
					signal_name = 'NameOwnerChanged')
		
		obj = self.bus.get_object ("org.freedesktop.DBus", "/")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		self.bus_interface.ListNames (reply_handler = self.list_names_handler, 
					      error_handler = self.list_names_error_handler)
	
		#listen for media key presses and act on them
		try:
			self.gnomeSettingsListner = self.bus.get_object('org.gnome.SettingsDaemon', '/org/gnome/SettingsDaemon/MediaKeys')
			self.gnomeSettingsListner.connect_to_signal("MediaPlayerKeyPressed", self.gnomesettings_signal_handler, dbus_interface='org.gnome.SettingsDaemon.MediaKeys')
		except:
			self.gnomeSettingsListner = None
	
	def dispose(self):
		self.owner_changed_signal.remove()
		self.clear_menu_buttons()

	def gnomesettings_signal_handler(*mmkeys):
		if not self.pithos:
			return
			
		for mmk in mmkeys:
			if mmk == "Play": #for me this key is mapped to play/pause so we default to that behaviour
				self.pithos.PlayPause()
			elif mmk == "Pause":
				self.pithos.PlayPause()
			elif mmk == "Stop":
				self.pithos.BanCurrentSong()
			elif mmk == "Next":
				self.pithos.SkipSong()
			elif mmk == "Previous":
				self.pithos.TiredCurrentSong()
				
	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	def list_names_handler(self, names):
		if DBUS_BUS in names:
			self.init_pithos_objects()
		else:
			self.items_unread = 0
			self.pithos = None
		self.set_menu_buttons()
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == DBUS_BUS:
			if new_owner:
				self.init_pithos_objects()
			else:
				self.items_unread = 0
				self.pithos = None
			self.set_menu_buttons()
	
	def init_pithos_objects(self):
		obj = self.bus.get_object (DBUS_BUS, DBUS_OBJECT_PATH)
		self.pithos = dbus.Interface (obj, DBUS_BUS)
		
		self.pithos.connect_to_signal("PlayStateChanged", self.play_state_changed)
		
		self.update_text()
	
	def clear_menu_buttons(self):
		for k in self.id_map.keys():
			self.remove_menu_item(k)
			self.menu_items_count = self.menu_items_count - 1
	
	def set_menu_buttons(self):
		self.clear_menu_buttons()
		
		if not self.pithos:
			return
		
		if self.pithos_is_playing():
			self.add_menu_item(TEXT_PAUSE, STATUS_ICON_PAUSE, DOCKY_NAME)
		else:
			self.add_menu_item(TEXT_PLAY, STATUS_ICON_PLAY, DOCKY_NAME)
			
		self.add_menu_item(TEXT_NEXT, STATUS_ICON_NEXT, DOCKY_NAME)
		self.add_menu_item(TEXT_LOVE, STATUS_ICON_LOVE, DOCKY_NAME)
		self.add_menu_item(TEXT_BAN, STATUS_ICON_BAN, DOCKY_NAME)
		self.add_menu_item(TEXT_TIRED, STATUS_ICON_TIRED, DOCKY_NAME)
		self.add_menu_item(TEXT_URL, STATUS_ICON_URL, DOCKY_NAME)
		
	def menu_pressed(self, menu_id):
		if not self.pithos:
			return
		
		menu_id = self.id_map[menu_id]
		
		if menu_id == TEXT_PLAY or menu_id == TEXT_PAUSE:
			self.pithos.PlayPause()
		elif menu_id == TEXT_NEXT:
			self.pithos.SkipSong()
		elif menu_id == TEXT_LOVE:
			self.pithos.LoveCurrentSong()
		elif menu_id == TEXT_BAN:
			self.pithos.BanCurrentSong()
		elif menu_id == TEXT_TIRED:
			self.pithos.TiredCurrentSong()
		elif menu_id == TEXT_URL:
			self.song_info_url()
			
	def song_info_url(self):
		if (self.song_url != None):
			webbrowser.open(self.song_url)
			
	def song_changed(self, info):
		if (info):
			self.song_info = '%s [%s] by %s' % (info['title'], info['album'], info['artist'])
			self.song_url = info['songDetailURL']
		else:
			self.song_info = None
			self.song_url = None
	
	def pithos_is_playing(self):
		if not self.pithos:
			return False
			
		return self.pithos.IsPlaying()
						
	def play_state_changed(self, state):
		self.set_menu_buttons()
		self.update_text()
		
	def update_text(self):
		self.reset_tooltip()
		
		if not self.pithos:
			return

		self.song_changed(self.pithos.GetCurrentSong())
		
		if (self.pithos_is_playing() and self.song_info != None):
			self.set_tooltip(self.song_info)
			
class DockyPithosSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("pithos.desktop"):
			self.items[pathtoitem] = DockyPithosItem(self, pathtoitem)

dockysink = DockyPithosSink()

def cleanup ():
	dockysink.dispose ()
			
if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)
	
	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))
	
	mainloop.run()
