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
	import urllib2
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink
	from dockmanager.dockmanager import RESOURCESDIR, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	print e
	exit()

enable_art_icon = True;
enable_badge_text = True;

art_icon_from_tag = True
try:
	import mutagen.mp3
	import mutagen.mp4
	from mutagen.id3 import ID3
	#from mutagen.flac import FLAC
except	ImportError, e:
	print "python-mutagen not available - art-icon from id3v2 tag turned off"
	art_icon_from_tag = False


rhythmboxbus = "org.gnome.Rhythmbox"
playerpath = "/org/gnome/Rhythmbox/Player"
playeriface = "org.gnome.Rhythmbox.Player"

shellpath = "/org/gnome/Rhythmbox/Shell"
shelliface = "org.gnome.Rhythmbox.Shell"

album_art_tmpfile = "/tmp/dockmanager_%s_rhythmbox_helper.png" % os.getenv('USERNAME')
album_art_file = "/tmp/dockmanager_%s_rhythmbox_helper.original.png" % os.getenv('USERNAME')

# 0 - none, 1- jewel, 2 - vinyl)
overlay = 2

class RhythmboxItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)

		self.player = None
		self.shell = None

		self.elapsed_secs = 0
		self.duration_secs = 0
		self.songinfo = None
		self.cover_basename = ""
		self.current_arturl = ""
		self.current_arturl_mtime = 0

		self.bus.add_signal_receiver(self.name_owner_changed_cb,
                                             dbus_interface='org.freedesktop.DBus',
                                             signal_name='NameOwnerChanged')
                                             
		obj = self.bus.get_object ("org.freedesktop.DBus", "/org/freedesktop/DBus")
		self.bus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
		
		self.bus_interface.ListNames (reply_handler=self.list_names_handler, error_handler=self.list_names_error_handler)

		self.bus.add_signal_receiver(self.signal_playingChanged, "playingChanged",  playeriface, rhythmboxbus, playerpath)
		self.bus.add_signal_receiver(self.signal_elapsedChanged, "elapsedChanged",  playeriface, rhythmboxbus, playerpath)
		self.bus.add_signal_receiver(self.signal_playingUriChanged, "playingUriChanged",  playeriface, rhythmboxbus, playerpath)
	
	def list_names_handler(self, names):
		if rhythmboxbus in names:
			self.init_rhythmbox_objects()
			self.set_menu_buttons()
			self.update_text()
			self.update_badge()
			self.update_icon()
	
			
	def list_names_error_handler(self, error):
		print "error getting bus names - %s" % str(error)
	
	
	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if name == rhythmboxbus:
			if new_owner:
				self.init_rhythmbox_objects()
			else:
				self.player = None
				self.shell = None
			self.set_menu_buttons()
			self.update_text()
			self.update_badge()
			self.update_icon()
	
	
	def init_rhythmbox_objects(self):
		obj = self.bus.get_object(rhythmboxbus, playerpath)
		self.player = dbus.Interface(obj, playeriface)

		obj = self.bus.get_object(rhythmboxbus, shellpath)
		self.shell = dbus.Interface(obj, shelliface)

		if self.player and self.shell:
			self.update_songinfo(self.player.getPlayingUri())

	def clear_menu_buttons(self):
		for k in self.id_map.keys():
			self.remove_menu_item(k)
	
	def set_menu_buttons(self):
		self.clear_menu_buttons()
				
		if not self.player:
			return
			
		self.add_menu_item("Previous", "media-skip-backward")
		if self.rhythmbox_is_playing():
			self.add_menu_item("Pause", "media-playback-pause")
		else:
			self.add_menu_item("Play", "media-playback-start")
		self.add_menu_item("Next", "media-skip-forward")
	
	def signal_playingChanged(self, state):
		self.set_menu_buttons()
		self.update_text()
		self.update_icon()

	def signal_elapsedChanged(self, value):
		self.elapsed_secs = value
		self.update_badge()

	def signal_playingUriChanged(self, newuri):
		self.update_songinfo(newuri)
		self.update_text()

	def update_songinfo(self, uri):
		if self.shell:
			try:
				song = dict(self.shell.getSongProperties(uri))
				self.duration_secs = song.get("duration")
				if self.duration_secs > 0:
					self.songinfo = '%s - %s (%i:%02i)' % (song.get("artist", "Unknown"), song.get("title", "Unknown"), song.get("duration") / 60, song.get("duration") % 60)
				else:
					self.songinfo = '%s - %s' % (song.get("artist", "Unknown"), song.get("title", "Unknown"))
				self.cover_basename = "%s - %s" % (song.get("artist"), song.get("album"))
			except dbus.DBusException, e:
				self.duration_secs = 0
				self.songinfo = None
				self.cover_basename = ""
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
		
		if self.rhythmbox_is_playing():
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
		if not self.player or not self.shell:
			return ""

		arturl = ""
		playinguri = self.player.getPlayingUri()
		filename = urllib2.unquote(playinguri).replace("file://", "");

		#1. Look in song folder
		#TODO need to replace some things, this is very weird
		coverdir = os.path.dirname(filename)
		covernames = ["cover.jpg", "cover.png", "Cover.jpg", "Cover.png", 
			"album.jpg", "album.png", "Album.jpg", "Album.png", 
			"albumart.jpg", "albumart.png", "Albumart.jpg", "Albumart.png", 
			"AlbumArt.jpg", "AlbumArt.png", 
			".folder.jpg", ".folder.png", ".Folder.jpg", ".Folder.png", 
			"folder.jpg", "folder.png", "Folder.jpg", "Folder.png"]
		for covername in covernames:
			arturl = os.path.join(coverdir, covername)
			if os.path.isfile(arturl):
				return arturl

		#2. Check rhythmbox dbus song properties
		arturl = str(self.shell.getSongProperties(playinguri).get("rb:coverArt-uri", ""))
		if not arturl == "":
			return urllib2.unquote(arturl).replace("file://", "");

		#3. Look for cached cover
		arturl = os.path.expanduser("~/.cache/rhythmbox/covers/%s.jpg" % self.cover_basename)

		#4. Look for image in tags
		if art_icon_from_tag:
			image_data = None
			loader = gtk.gdk.PixbufLoader()
			properties = self.shell.getSongProperties(playinguri)
			mimetype = properties["mimetype"]
			if mimetype == "application/x-id3":
				try:
					f = ID3(filename)
				except:
					print "No ID3 tags in %s" % filename
					return arturl
				apicframes = f.getall("APIC")
				if len(apicframes) >= 1:
					frame = apicframes[0]
					image_data = frame.data
					
			elif mimetype == "audio/x-aac":
				try:
					f = mutagen.mp4.MP4(filename)
				except:
					print "MP4 couldn't open %s" % filename
					return arturl
					
				if "covr" in f.tags:
					covertag = f.tags["covr"][0]
					image_data = covertag
					
			elif mimetype == "audio/x-flac":
				#f = FLAC(filename)
				print "cover from FLAC not implemented"
					
			if image_data:
				try:
					loader.write(image_data)
					loader.close()
					pixbuf = loader.get_pixbuf()
					pixbuf.scale_simple(250, 250, gtk.gdk.INTERP_NEAREST).save(album_art_file, "png", {})
					return album_art_file
				except Exception, e:
					print "problem with image_data from %s" % filename
					print e
			try:
				loader.close()
			except:
				return arturl
			
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
		if not self.shell or not self.player:
			self.reset_tooltip()

		if self.rhythmbox_is_playing() and self.songinfo:
			self.set_tooltip(self.songinfo)
		else:
			self.reset_tooltip()

	def update_badge(self):
		if not self.player:
			self.reset_badge()
		
		if not enable_badge_text:
			return True
		
		if self.rhythmbox_is_playing():
			#if song length is 0 then counting up instead of down
			if self.duration_secs > 0:
				position = self.duration_secs - self.elapsed_secs
			else:
				position = self.elapsed_secs
			string = '%i:%02i' % (position / 60, position % 60)
			self.set_badge(string)
		else:
			self.reset_badge()
	
	def menu_pressed(self, menu_id):
		if self.id_map[menu_id] == "Play":
			self.rhythmbox_playPause()
		elif self.id_map[menu_id] == "Pause":
			self.rhythmbox_playPause()
		elif self.id_map[menu_id] == "Next":
			self.rhythmbox_next()
		elif self.id_map[menu_id] == "Previous":
			self.rhythmbox_prev()
		
	def rhythmbox_playPause(self):
		if self.player:
			self.player.playPause(True)
		
	def rhythmbox_next(self):
		if self.player:
			self.player.next()
		
	def rhythmbox_prev(self):
		if self.player:
			self.player.previous()
	
	def rhythmbox_is_playing(self):
		if self.player:
			try:
				return self.player.getPlaying() == 1
			except dbus.DBusException, e:
				return False		
		return False
		
class RhythmboxSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("rhythmbox.desktop"):
			self.items[pathtoitem] = RhythmboxItem(self, pathtoitem)

rhythmboxsink = RhythmboxSink()

def cleanup ():
	rhythmboxsink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	while mainloop.is_running():
		mainloop.run()
