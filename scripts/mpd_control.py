#!/usr/bin/env python

#
# Copyright (C) 2010 Felipe Morales
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import gobject
import glib
import dbus
import dbus.glib
import atexit
import socket, errno
from signal import signal, SIGTERM
import sys, os
import ConfigParser

try:
	from mpd import MPDClient
except ImportError, e:
	sys.stderr.write("mpd-control: python-mpd is needed\n")
	sys.exit()
try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
except ImportError, e:
	sys.stderr.write("mpd-control: python-dockmanager is needed\n")
	sys.exit()

class DockManagerMPDItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)

		self.add_menu_item("Previous", "media-skip-backward", "MPD Controls")
		self.add_menu_item("Play/Pause", "media-playback-start", "MPD Controls")
		self.add_menu_item("Next", "media-skip-forward", "MPD Controls")

		# add a timed function that updates the item tooltip
		gobject.timeout_add(1000, self.update_title)
	
	def update_title(self):
		if self.sink.client_is_usable():
			#if there's an active song
			if self.sink.mpdclient.currentsong() != {}:
				# we'll gran the info we need from it.
				songdata = self.sink.mpdclient.currentsong()
			# if there isn't, but the playlist isn't empty
			elif self.sink.mpdclient.playlistinfo() != []:
				# we'll grab the info we need from the first song in it
				# (if we toggle playback, that's what will play)
				songdata = self.sink.mpdclient.playlistinfo()[0]
			else:
				self.set_tooltip("[nothing to play]")
				return True
			
			tail = self.sink.get_tail()
			title = self.sink.get_title(songdata)
			artist = self.sink.get_artist(songdata)
			
			if artist != "":
				self.set_tooltip(artist + " - " +  title + tail)
			else:
				self.set_tooltip(title + tail)

		return True

	def menu_pressed(self, menu_id):
		if self.id_map[menu_id] == "Play/Pause":
			self.sink.handle_actions("toggle")
		elif self.id_map[menu_id] == "Next":
			self.sink.handle_actions("next")
		elif self.id_map[menu_id] == "Previous":    
			self.sink.handle_actions("prev")

class DockManagerMPDSink(DockManagerSink):
	def __init__(self):
		DockManagerSink.__init__(self)

		# initialize self.mpdclient
		self.client_setup()

		# try to grab the multimedia keys
		self.grab_mediakeys()

	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith(("sonata.desktop", "gmpc.desktop", "ario.desktop", "gbemol.desktop")):
			self.items[pathtoitem] = DockManagerMPDItem(self, pathtoitem)

	def client_setup(self):
		try:
			self.mpdclient = MPDClient()
			self.get_config()
			self.mpdclient.connect(self.host, self.port)
			if self.password not in ("", None):
				self.mpdclient.password(self.password)
		except:
			sys.stderr.write("mpd-control: couldn't setup the client\n")
			sys.exit()

	def get_config(self):
		if self.get_config_from_sonata():
			return
		elif self.get_config_from_mpdconf("~/.mpdconf"):
			return
		elif self.get_config_from_mpdconf("/etc/mpd.conf"):
			return
		self.host = "localhost"
		self.port = 6600
		self.password = None

	def get_config_from_sonata(self):
		conf = ConfigParser.ConfigParser()
		if os.path.isfile(os.path.expanduser('~/.config/sonata/sonatarc')):
			conf.read(os.path.expanduser('~/.config/sonata/sonatarc'))
			if conf.has_option('connection', 'profile_num'):
				profile_num = conf.get('connection', 'profile_num')
				self.host=(conf.get('profiles', 'hosts[' + profile_num + ']'))
				self.port=(conf.getint('profiles', 'ports[' + profile_num + ']'))
				self.password=(conf.get('profiles', 'passwords[' + profile_num + ']'))
				return True		
		return False

	def get_config_from_mpdconf(self, path):
		self.host = "localhost"
		if os.path.isfile(os.path.expanduser(path)):
			conf = file(os.path.expanduser(path), "r")
			lines = conf.readlines()
			for line in lines:
				setting = line.split()
				if setting[0] == "bind_to_address":
					self.host = setting[1].replace('"', '')
				if setting[0] == "#port" or setting[0] == "port":
					self.port = int(setting[1].replace('"', ''))
				if setting[0] == "password":
					self.password == setting[1].replace('"', '').split("@")[0]
				elif setting[0] == "#password":
					self.password == None
		return False
		
	# check if the pipe python-mpd client needs to work is broken or not
	def client_is_usable(self):
		try:
			self.mpdclient.status()
		except socket.error, e:
			if e.errno == errno.EPIPE:
				self.client_setup()
				return False
		return True
	
	# grab multimedia keys
	def grab_mediakeys(self):
		try:
			bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
			keysbus = bus.get_object("org.gnome.SettingsDaemon", "/org/gnome/SettingsDaemon/MediaKeys")
			keysbus.GrabMediaPlayerKeys("mpd-control", 0, dbus_interface="org.gnome.SettingsDaemon.MediaKeys")
			keysbus.connect_to_signal("MediaPlayerKeyPressed", self.delegate_mediakeys)
		except:
			sys.stdout.write("mpd-control: couldn't grab media keys\n")

	# activates actions from the multimedya keys
	def delegate_mediakeys(self, *mmkeys):
		for key in mmkeys:
			if key == "Play":
				self.handle_actions("toggle")
			elif key == "Stop":
				self.handle_actions("stop")
			elif key == "Next":
				self.handle_actions("next")
			elif key == "Previous":
				self.handle_actions("prev")

	# the real action handler
	def handle_actions(self, action):
		if self.client_is_usable():
			if action == "toggle":
				if self.mpdclient.playlistinfo() != []: # we have a playlist
					if self.mpdclient.currentsong() != {}: # we have a selected song
						state = self.mpdclient.status()['state'] 
						if state == "stop": # if it's stopped, play from current selected song
							self.mpdclient.play()
						elif state in ("play", "pause"): #if it's playing or paused, toggle the state
							self.mpdclient.pause()
					else:
						self.mpdclient.play() # play from playlist start
			elif action == "prev":
				self.mpdclient.previous()
			elif action == "next":
				self.mpdclient.next()
			elif action == "stop":
				self.mpdclient.stop()

	# Returns the client status as a string 
	def get_tail(self):
		if self.mpdclient.status()['state'] == 'stop':
			return " [stopped]"
		elif self.mpdclient.status()['state'] == 'pause':
			return " [paused]"
		else:
			return ""

	# Returns song title
	def get_title(self, songdata):
		if songdata.has_key("title"):
			if songdata.has_key("name"): # we can assume it's a radio or stream
				# we split the title from the info we have
				# for streams, "title" is usually of the form "artist - title"
				return songdata["title"].split(" - ")[1]
			else:
				return songdata["title"]
		else: # there's no data
			return songdata["file"] # we return the file path

	# Returns song artist
	def get_artist(self, songdata):
		if songdata.has_key("name"): # we can assume it's a radio or stream
			if songdata.has_key("title"): # we grab the artist info from the title
				return songdata["title"].split(" - ")[0]
			else:
				return ""
		elif songdata.has_key("artist"):
			return songdata["artist"]
		else: #there's no data
			return ""

sink = DockManagerMPDSink()

def cleanup():
	sink.dispose()

if __name__ == "__main__":
	mainloop = gobject.MainLoop()

	atexit.register(cleanup)
	signal(SIGTERM, lambda signum, stacj_frame: sys.exit(1))

	mainloop.run()
