#!/usr/bin/env python

#
#  Copyright (C) 2010 Pawel Bara
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
import dbus
import gobject
import os

try:
	import gtk
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink
	from dockmanager.dockmanager import DOCKITEM_IFACE, RESOURCESDIR
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	print e
	exit()


# cover overlay related constants
album_art_tmpfile = "/tmp/dockmanager_%s_clementine_control.png" % os.getenv('USERNAME')

# 0 - none, 1 - jewel, 2 - vinyl
overlay = 2


freedesktop_iface_name = 'org.freedesktop.DBus.Properties'

def connect_to_dbus_properties_changed(dbus_object, callback):
	"""
	Connects the callback with the 'PropertiesChanged' signal of the
	dbus_object.
	"""

	property_iface = dbus.Interface(dbus_object, dbus_interface=freedesktop_iface_name)
	return property_iface.connect_to_signal('PropertiesChanged', callback)

def get_dbus_property(dbus_object, property_name):
	"""
	Gets current value of the property property_name from the dbus_object.
	"""

	property_iface = dbus.Interface(dbus_object, dbus_interface=freedesktop_iface_name)
	return property_iface.Get(dbus_object.dbus_interface, property_name)


class ClementineItem(DockManagerItem):
	"""
	Clementine's helper. It's working while Clementine's on and pauses when
	Clementine is being closed.

	It's functionalities are:
	- control menu for Clementine. It always has the "next", "previous" and
	  "stop" controls. It also has a "play" or "pause" control, depending on
	  the current PlaybackStatus of Clementine
	- tooltip with information about the current song
	- badge with the now-playing time of the current song
	- the current cover art as the Clementine's icon on the dock
	"""

	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)

		self.timer = None

		self.synch_counter = 0
		self.pos = 0

		self.clementine = ClementineDBusFacade(self.turn_helper_on,
											   self.turn_helper_off,
											   self.on_playback_status_changed,
											   self.on_song_changed,
											   self.on_cover_art_changed,
											   self.on_seeked)

	def turn_helper_on(self):
		"""
		Effectively turn's helper on (after every Clementine's
		startup).
		"""

		self.prepare_menu()

		self.update_tooltip()

		self.update_badge()
		self.set_timer()

		self.change_cover_art()

	def turn_helper_off(self):
		"""
		Effectively turn's helper off (after every Clementine's
		shutdown).
		"""

		self.reset_icon()

		self.stop_timer()
		self.reset_badge()

		self.reset_tooltip()

		self.clear_menu()

	def prepare_menu(self, is_playing=None):
		"""
		Recreates the menu of the helper.

		The is_playing flag indicates which button will be shown (play or
		pause). If the flag's value is not given, it will be determined by
		the method.
		"""

		self.clear_menu()

		try:

			if is_playing is None:
				is_playing = self.clementine.check_is_playing()

		except ClementineTurnedOffError:

			# leave menu empty if Clementine's off
			return

		self.add_menu_item("Previous", "media-skip-backward")

		if is_playing:
			self.add_menu_item("Pause", "media-playback-pause")
		else:
			self.add_menu_item("Play", "media-playback-start")

		self.add_menu_item("Stop", "media-playback-stop")
		self.add_menu_item("Next", "media-skip-forward")

	def clear_menu(self):
		"""
		Clears menu of the helper.
		"""

		for k in self.id_map.keys():
			self.remove_menu_item(k)

	def on_seeked(self, position):
		"""
		Moves time marker when Clementine's been seeked.
		"""

		self.pos = position
		self.update_badge()

	def update_badge(self):
		"""
		Updates the helper's badge with the now-playing time. The method
		can be used from timers (returns boolean indicating whether
		something went wrong).
		"""

		try:

			# synchronize position with Clementine every tenth timer's tick
			if(self.synch_counter % 10 == 0):
				self.pos = self.clementine.get_play_time()
			else:
				self.pos += 1000000

			self.synch_counter += 1

		except ClementineTurnedOffError:

			# if Clementine's off, reset the badge
			self.reset_badge()
			return False

		if self.pos == 0:
			self.reset_badge()
		else:
			pos = self.pos / 1000000
			badge_text = '%i:%02i' % (pos / 60, pos % 60)

			self.set_badge(badge_text)

		return True

	def update_tooltip(self, song_info=None):
		"""
		Updates the helper's tooltip with basic information about
		the currently playing song.

		If the information (song's metadata) is not given,
		it will try to determine those itself.
		"""

		try:
			if song_info is None:
				song_info = self.clementine.get_current_song_metadata()
		except ClementineTurnedOffError:
			# if Clementine's off, reset the tooltip
			self.reset_tooltip()
			return

		if self.proper_metadata(song_info):
			# first artist from artist's list or Unknown if there's none
			artist = song_info.get("xesam:artist", ["Unknown"])[0]
			if len(artist) == 0:
				artist = "Unknown"

			# do we know the length of the song?
			if 'mpris:length' in song_info:
				# duration is in microseconds - translating it to seconds
				duration = song_info['mpris:length'] / 1000000

				final_info = '%s - %s  (%i:%02i)' % (artist,
													 song_info.get("xesam:title", "Unknown"),
													 duration / 60, duration % 60)
			else:
				final_info = '%s - %s  (?)' % (artist,
											   song_info.get("xesam:title", "Unknown"))

			self.set_tooltip(final_info)

		else:

			self.reset_tooltip()

	def proper_metadata(self, metadata):
		return metadata != None and len(metadata) > 0

	def start_timer(self):
		"""
		Starts the timer that updates the "current time" badge.
		"""

		self.stop_timer()

		if not self.timer:
			self.timer = gobject.timeout_add (1000, self.update_badge)

	def stop_timer(self):
		"""
		Stops the timer that updates the "current time" badge.
		"""

		self.synch_counter = 0
		self.pos = 0

		if self.timer:
			gobject.source_remove (self.timer)
			self.timer = None

	def change_cover_art(self, cover_art_url=None):
		"""
		Changes the helper's icon to icon from file 'cover_art_url'.
		"""

		try:

			# initial phase - 'pull' the overlayed covert art's path (if any)
			if cover_art_url is None:
				cover_art_url = self.clementine.get_path_for_overlayed_cover()

		except ClementineTurnedOffError:

			# reset icon if Clementine's off or no song is currently playing
			self.reset_icon()
			return

		if cover_art_url is not None:
			self.set_icon(cover_art_url)
		else:
			self.reset_icon()

	def reset(self):
		"""
		Resets the helper.
		"""

		self.reset_icon()
		self.stop_timer()
		self.reset_badge()
		self.reset_tooltip()

	def on_playback_status_changed(self, new_playback_status):
		"""
		The callback for changes of Clementine's PlaybackStatus.
		"""

		self.set_timer(new_playback_status)

		is_playing = self.clementine.is_playing(new_playback_status)

		# reset the helper if Clementine's been stopped
		if self.clementine.is_stopped(new_playback_status):
			self.reset()

		# recreate the helper's menu
		self.prepare_menu(is_playing)

	def set_timer(self, playback_status=None):
		"""
		Turns the badge's timer on or off depending on the Clementine's
		current PlaybackStatus.
		"""

		try:
			if playback_status == None:
				is_playing = self.clementine.check_is_playing()
			else:
				is_playing = self.clementine.is_playing(playback_status)

			# pausing the badge's timer when current song is
			# paused or stopped
			if is_playing:
				self.start_timer()
			else:
				self.stop_timer()

		except ClementineTurnedOffError:
			# Clementine's off - stop the badge timer
			self.stop_timer()

	def on_song_changed(self, new_metadata):
		"""
		The callback for changes of the currently playing Clementine's song.
		"""

		if 'mpris:trackid' in new_metadata:
			self.update_tooltip(new_metadata)
			self.reset_badge()

			# change the cover art too if it's already present in the message
			try:
				if 'mpris:artUrl' in new_metadata:
					overlayed = self.clementine.get_path_for_overlayed_cover()
					self.change_cover_art(overlayed)
			except ClementineTurnedOffError:
				self.reset_icon()
		else:
			self.reset()

	def on_cover_art_changed(self, cover_art_url):
		"""
		The callback for changes of the current cover art in Clementine.
		"""

		if cover_art_url != None:
			self.change_cover_art(cover_art_url)
		else:
			self.reset_icon()

	def menu_pressed(self, menu_id):
		"""
		Performs an action invoked by clicking one of the helper's context
		menu items.
		"""

		try:

			if self.id_map[menu_id] == "Previous":
				self.clementine.prev()
			elif self.id_map[menu_id] == "Stop":
				self.clementine.stop()
			elif self.id_map[menu_id] == "Play":
				self.clementine.play()
			elif self.id_map[menu_id] == "Pause":
				self.clementine.pause()
			elif self.id_map[menu_id] == "Next":
				self.clementine.next()

		except ClementineTurnedOffError:

			# Clementine's off - do nothing
			return


clementine_bus_name = "org.mpris.MediaPlayer2.clementine"

player_object_path = "/org/mpris/MediaPlayer2"
player_iface_name = "org.mpris.MediaPlayer2.Player"

tlist_object_path = "/org/mpris/MediaPlayer2"
tlist_iface_name = "org.mpris.MediaPlayer2.Tracklist"

class ClementineDBusFacade:

	def __init__(self, on_callback, off_callback, playback_status_changed_callback,
				 song_changed_callback, cover_art_changed_callback, seeked_callback):
		self.on_callback = on_callback
		self.off_callback = off_callback
		self.playback_status_changed_callback = playback_status_changed_callback
		self.song_changed_callback = song_changed_callback
		self.cover_art_changed_callback = cover_art_changed_callback
		self.seeked_callback = seeked_callback

		self.cl_player = None
		self.cl_tlist = None

		self.bus = dbus.SessionBus()
		# we track Clementine's on / off status
		self.bus.watch_name_owner(clementine_bus_name, self.on_dbus_name_change)

	def is_on(self):
		"""
		Returns a flag saying whether Clementine's on.
		"""

		return self.cl_player is not None

	def prev(self):
		"""
		Changes the current song to the previous one. Might throw
		ClementineTurnedOffError if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		self.cl_player.Previous()

	def stop(self):
		"""
		Stops Clementine's playback. Might throw ClementineTurnedOffError
		if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		self.cl_player.Stop()

	def pause(self):
		"""
		Pauses Clementine's playback. Might throw ClementineTurnedOffError
		if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		self.cl_player.Pause()

	def play(self):
		"""
		Starts Clementine's playback. Might throw ClementineTurnedOffError
		if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		self.cl_player.Play()

	def next(self):
		"""
		Changes the current song to the next one. Might throw
		ClementineTurnedOffError if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		self.cl_player.Next()

	def get_play_time(self):
		"""
		Gets the current song's now-playing position in microseconds. Might
		throw ClementineTurnedOffError if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		return get_dbus_property(self.cl_player, 'Position')

	def get_current_song_metadata(self):
		"""
		Returns all of the current song's metadata. Might throw
		ClementineTurnedOffError if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		return get_dbus_property(self.cl_player, 'Metadata')

	def check_is_playing(self):
		"""
		Checks whether Clementine is currently playing a song. Might
		throw ClementineTurnedOffError if Clementine's been turned off.
		"""

		if not self.is_on():
			raise ClementineTurnedOffError()

		playback_status = get_dbus_property(self.cl_player, 'PlaybackStatus')
		return self.is_playing(playback_status)

	def is_playing(self, status):
		"""
		Decodes Clementine's status and returns a flag saying whether it's
		currently playing a song.
		"""

		return status == 'Playing'

	def is_stopped(self, status):
		"""
		Decodes Clementine's status and returns a flag saying whether it's
		currently stopped.
		"""

		return status == 'Stopped'

	def on_properties_changed(self, iface_name, changed_props, invalidated_props):
		"""
		A callback for the Clementine's 'PropertiesChanged' signal.
		"""

		if iface_name == player_iface_name:

			if('PlaybackStatus' in changed_props):
				self.playback_status_changed_callback(changed_props['PlaybackStatus'])

			if('Metadata' in changed_props):
				self.song_changed_callback(changed_props['Metadata'])

				try:
					cover_art = changed_props['Metadata']['mpris:artUrl']
					cover_art = cover_art[len('file://'):]

					# only if it's a valid file
					if os.path.isfile(cover_art):
						mtime = os.stat(cover_art).st_mtime

						# only if there really was a change
						if self.last_cover_art != cover_art or self.last_cover_art_mtime != mtime:
							self.last_cover_art = cover_art
							self.last_cover_art_mtime = mtime

							self.cover_art_changed_callback(self.get_album_art_overlay_path(cover_art))
					else:
						raise KeyError

				except KeyError:
					# Clementine is now not playing anything or the current
					# song has no cover
					self.last_cover_art = None
					self.last_cover_art_mtime = None

					self.cover_art_changed_callback(None)

	def get_path_for_overlayed_cover(self):
		"""
		Overlays the cover of currently playing song and then returns the path
		to the overlayed cover file. Returns 'None' if there's nothing playing.
		Might throw ClementineTurnedOffError if Clementine's been turned off.
		"""

		metadata = self.get_current_song_metadata()

		try:
			cover_art = metadata['mpris:artUrl']
			cover_art = cover_art[len('file://'):]
			return self.get_album_art_overlay_path(cover_art)
		except KeyError:
			return None

	# taken from rhythmbox_control.py
	def get_album_art_overlay_path(self, picfile):
		"""
		Adds an overlay to the cover art.
		"""

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
			pb.composite(pb_result, 30, 21, 200, 200, 30, 21, 200.0 / pb.get_width(), 200.0 / pb.get_height(), gtk.gdk.INTERP_BILINEAR, 255)
		elif overlay == 2:
			overlayfile = os.path.join(RESOURCESDIR, "albumoverlay_vinyl.png")
			pb.composite(pb_result, 3, 26, 190, 190, 3, 26, 190.0 / pb.get_width(), 190.0 / pb.get_height(), gtk.gdk.INTERP_BILINEAR, 255)
		else:
			return picfile

		pb_overlay = gtk.gdk.pixbuf_new_from_file_at_size(overlayfile, 250, 250)
		pb_overlay.composite(pb_result, 0, 0, 250, 250, 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
		pb_result.save(album_art_tmpfile, "png", {})

		return album_art_tmpfile

	def on_dbus_name_change(self, connection_name):
		"""
		This method effectively tracks down the events of Clementine app starting
		and shutting down. When the app shuts down, this callback nullifies our
		Clementine's proxies and when the app starts, the callback sets the valid
		proxies again.
		"""

		if len(connection_name) != 0:
			bus_object = self.bus.get_object(connection_name, player_object_path)
			self.cl_player = dbus.Interface(bus_object, player_iface_name)

			bus_object = self.bus.get_object(connection_name, player_object_path)
			self.cl_player.connect_to_signal('Seeked', self.seeked_callback)

			bus_object = self.bus.get_object(connection_name, tlist_object_path)
			self.cl_tlist = dbus.Interface(bus_object, tlist_iface_name)

			try:
				cover_path = get_dbus_property(self.cl_player, 'Metadata')['mpris:artUrl']

				if os.path.isfile(cover_path):
					self.last_cover_art = self.get_album_art_overlay_path(cover_path)
					self.last_cover_art_mtime = os.stat(cover_path).st_mtime
				else:
					raise KeyError

			except KeyError, DBusException:
				self.last_cover_art = None
				self.last_cover_art_mtime = None

			connect_to_dbus_properties_changed(self.cl_player, self.on_properties_changed)

			self.on_callback()

		else:
			self.cl_player = None
			self.cl_tlist = None

			self.off_callback()


class ClementineTurnedOffError(Exception):
	"""
	Indicates that user requested an operation that requires Clementine
	to be on while it was turned off.
	"""

	pass


class ClementineSink(DockManagerSink):

	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith("clementine.desktop"):
			self.items[pathtoitem] = ClementineItem(self, pathtoitem)


clementine_sink = ClementineSink()

def cleanup ():
	clementine_sink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	while mainloop.is_running():
		mainloop.run()
