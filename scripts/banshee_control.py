#!/usr/bin/env python

#  
#  Copyright (C) 2009-2010 Jason Smith, Rico Tzschichholz, Robert Dyer
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
	import gtk
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from dockmanager.dockmanager import RESOURCESDIR
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	print e
	exit()

bansheebus = "org.bansheeproject.Banshee"
playerpath = "/org/bansheeproject/Banshee/PlayerEngine"
playeriface = "org.bansheeproject.Banshee.PlayerEngine"

controlpath = "/org/bansheeproject/Banshee/PlaybackController"
controliface = "org.bansheeproject.Banshee.PlaybackController"

enable_art_icon = True;
enable_badge_text = True;

album_art_tmpfile = "/tmp/dockmanager_%s_banshee_helper.png" % os.getenv('USERNAME')

# 0 - none, 1- jewel, 2 - vinyl)
overlay = 2

class BansheeItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.timer = 0
		self.player = None
		self.control = None
		
		self.duration_secs = 0
		self.songinfo = None
		self.current_arturl = ""
		self.current_arturl_mtime = 0
				
		self.bus.add_signal_receiver(self.name_owner_changed_cb,
                                             dbus_interface='org.freedesktop.DBus',
                                             signal_name='NameOwnerChanged')
                                             
		obj = self.bus.get_object ("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		
		self.bus_interface.ListNames (reply_handler=self.list_names_handler, error_handler=self.list_names_error_handler)
	
		self.bus.add_signal_receiver(self.signal_EventChanged, "EventChanged",  playeriface, bansheebus, playerpath)
		self.bus.add_signal_receiver(self.signal_StateChanged, "StateChanged",  playeriface, bansheebus, playerpath)

	def list_names_handler(self, names):
		if bansheebus in names:
			self.init_banshee_objects()
			self.set_menu_buttons()
			self.update_text()			
			self.update_badge()
			self.update_icon()

	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == bansheebus:
			if new_owner:
				self.init_banshee_objects()
			else:
				self.player = None
				self.control = None
				self.stop_timer()
				self.set_menu_buttons()
				self.update_text()			
				self.update_badge()
				self.update_icon()
	
	def start_timer(self):
		if not self.timer > 0:
			self.timer = gobject.timeout_add (1000, self.update_badge)
	
	def stop_timer(self):
		if self.timer > 0:
			gobject.source_remove (self.timer)
			self.timer = 0
	
	def init_banshee_objects(self):
		obj = self.bus.get_object(bansheebus, playerpath)
		self.player = dbus.Interface(obj, playeriface)
		
		obj = self.bus.get_object(bansheebus, controlpath)
		self.control = dbus.Interface(obj, controliface)
		
		if self.player:
			self.update_songinfo()
		
		if self.banshee_is_playing():
			self.start_timer()

	def clear_menu_buttons(self):
		for k in self.id_map.keys():
			self.remove_menu_item(k)
	
	def set_menu_buttons(self):
		self.clear_menu_buttons()
		
		if not self.player:
			return

		self.add_menu_item("Previous", "media-skip-backward")
		if self.banshee_is_playing():
			self.add_menu_item("Pause", "media-playback-pause")
		else:
			self.add_menu_item("Play", "media-playback-start")
		self.add_menu_item("Next", "media-skip-forward")
	
	def signal_EventChanged(self, event, st, value):
		print "EventChanged: %s" % (event)	
		if (event in ["startofstream", "trackinfoupdated"]):
			self.update_songinfo();
			self.update_text()
			self.update_badge()
			self.update_icon()
		elif (event in ["endofstream"]):
			self.update_icon()
			self.update_text()
		elif (event in ["seek"]):
			self.update_badge()

	def signal_StateChanged(self, state):
		print "StateChanged: %s" % (state)	
		self.set_menu_buttons()
		self.update_text()

		if state == "playing":
			self.start_timer()
		else:
			self.stop_timer()
			
	def update_songinfo(self):
		if self.player:
			try:
				song = self.player.GetCurrentTrack()
				self.duration_secs = self.player.GetLength() / 1000
				if self.duration_secs > 0:
					self.songinfo = '%s - %s (%i:%02i)' % (song.get("artist", "Unknown"), song.get("name", "Unknown"), self.duration_secs / 60, self.duration_secs % 60)
				else:
					self.songinfo = '%s - %s' % (song.get("artist", "Unknown"), song.get("name", "Unknown"))
			except dbus.DBusException, e:
				self.duration_secs = 0
				self.songinfo = None
			return
		self.duration_secs = 0
		self.songinfo = None
	
	def update_icon(self):
		if not self.player:
			self.current_arturl = ""
			self.reset_icon()
			return False
			
		if not enable_art_icon:
			return True
		
		if self.banshee_is_playing():
			arturl = self.get_album_art_path()
			# Add overlay to cover
			if os.path.isfile(arturl):
				if self.current_arturl == arturl and self.current_arturl_mtime == os.stat(arturl).st_mtime:
					return True
				self.current_arturl = arturl
				self.current_arturl_mtime = os.stat(arturl).st_mtime
				self.set_icon(self.get_album_art_overlay_path(arturl))
			else:
				self.current_arturl = ""
				self.reset_icon()
		else:
			self.current_arturl = ""
			self.reset_icon()
		return True
		
	def get_album_art_path(self):
		artwork_id = self.player.GetCurrentTrack().get("artwork-id")

		if not self.player or not artwork_id:
			return ""

		arturl = os.path.expanduser("~/.cache/media-art/%s.jpg" % artwork_id)
		if not os.path.isfile(arturl):
			arturl = os.path.expanduser("~/.cache/album-art/%s.jpg" % artwork_id)

		return arturl

	def get_album_art_overlay_path(self, picfile):
		if overlay == 0:
			return picfile

		try:
			pb = gtk.gdk.pixbuf_new_from_file(picfile)
		except Exception, e:
			print e
			return picfile
		
		pb_result = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 250, 250)
		pb_result.fill(0x00000000)

		if overlay == 1:
			overlayfile = os.path.join(RESOURCESDIR, "albumoverlay_jewel.png")
			pb.composite(pb_result, 30, 21, 200, 200, 30, 21, 200.0/pb.get_width(), 200.0/pb.get_height(), gtk.gdk.INTERP_BILINEAR, 255)
		elif overlay == 2:
			overlayfile = os.path.join(RESOURCESDIR, "albumoverlay_vinyl.png")
			pb.composite(pb_result, 3, 26, 190, 190, 3, 26, 190.0/pb.get_width(), 190.0/pb.get_height(), gtk.gdk.INTERP_BILINEAR, 255)
		else:
			return picfile

		pb_overlay = gtk.gdk.pixbuf_new_from_file_at_size(overlayfile, 250, 250)
		pb_overlay.composite(pb_result, 0, 0, 250, 250, 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
		pb_result.save(album_art_tmpfile, "png", {})
		
		return album_art_tmpfile

	def update_text(self):
		if not self.player:
			self.reset_tooltip()

		if self.banshee_is_playing() and self.songinfo:
			self.set_tooltip(self.songinfo)
		else:
			self.reset_tooltip()
	
	def update_badge(self):
		if not self.player:
			self.reset_badge()
			return False

		if not enable_badge_text:
			return True
		
		if self.banshee_is_playing():
			#if song length is 0 then counting up instead of down
			if self.duration_secs > 0:
				position = self.duration_secs - self.player.GetPosition() / 1000
			else:
				position = self.player.GetPosition() / 1000
			string = '%i:%02i' % (position / 60, position % 60)
			self.set_badge(string)
		else:
			self.reset_badge()
		return True
	
	def menu_pressed(self, menu_id):
		if not self.player:
			return False
		
		if self.id_map[menu_id] == "Play":
			self.player.Play()
		elif self.id_map[menu_id] == "Pause":
			self.player.Pause()
		elif self.id_map[menu_id] == "Next":
			self.control.Next(False)
		elif self.id_map[menu_id] == "Previous":
			self.control.Previous(False)
		
	def banshee_is_playing(self):
		if self.player:
			try:
				return self.player.GetCurrentState() == "playing"
			except dbus.DBusException, e:
				return False
		return False
	

class BansheeSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("banshee-1.desktop") or item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("banshee.desktop"):
			self.items[pathtoitem] = BansheeItem(self, pathtoitem)

bansheesink = BansheeSink()

def cleanup ():
	bansheesink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	while mainloop.is_running():
		mainloop.run()
