#!/usr/bin/env python

#  
#  Copyright (C) 2010 Rico Tzschichholz, Robert Dyer, Igor Gevka
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

try:
	from twisted.internet import glib2reactor # for gtk-2.0
	glib2reactor.install()
	
	from deluge.ui.client import client
	from twisted.internet import reactor
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
	from gobject import timeout_add
except ImportError, e:
	print e
	exit()

debugConnections = False
showRateOver = 5000
rate = 0

delugeDaemon = None

def daemon_disconnect_callback():
	if debugConnections:	
		print "Disconnected from deluge daemon. Will try to reconnect."
	ConnectToDaemon()

def ConnectToDaemon():
	global delugeDaemon	
	host="localhost"
	port=58846
	user=""
	password=""
	client.set_disconnect_callback(daemon_disconnect_callback)
	if debugConnections:
		print "Connecting to deluge daemon..."
	delugeDaemon = client.connect(host, port, user, password)

ConnectToDaemon()

def on_connect_success(result):
	def on_get_config_value(value, key):
		global rate
		rate=value[key]
	client.core.get_session_status(["download_rate"]).addCallback(on_get_config_value,"download_rate")

def on_connect_fail(result):
	if debugConnections:	
		print "Connection failed with result ", result, ", reconnecting."
	global rate
	rate = 0
	ConnectToDaemon()
	return False



def bytes2ratestr(bytes):
	for factor, suffix in (
		(1024 ** 5, 'P'),
		(1024 ** 4, 'T'), 
		(1024 ** 3, 'G'), 
		(1024 ** 2, 'M'), 
		(1024 ** 1, 'K'),
		(1024 ** 0, 'B')):
		if bytes >= factor:
			break
	amount = int(bytes / factor)
	return str(amount) + suffix
	

class DelugeItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		
		self.timer = 0
		
		if not self.timer > 0:
			self.timer = timeout_add (2000, self.update_badge)
		
		self.set_menu_buttons()

	def update_badge(self):
		global delugeDaemon
		global rate		
		try:
			delugeDaemon.addCallback(on_connect_success)
			delugeDaemon.addErrback(on_connect_fail)
			
			if rate > showRateOver:
				self.set_badge("%s" % bytes2ratestr(round(rate)))
			else:
				self.reset_badge()
			return True
		except Exception, e:
			print "Deluge badge exception:", e
			self.reset_badge()
			return False
	
	def clear_menu_buttons(self):
		for k in self.id_map.keys():
			self.remove_menu_item(k)
	
	def set_menu_buttons(self):
		self.clear_menu_buttons()
		
		self.add_menu_item("Pause All", "media-playback-pause")
		self.add_menu_item("Resume All", "media-playback-start")

	def menu_pressed(self, menu_id):
		
		if self.id_map[menu_id] == "Pause All":
			client.core.pause_all_torrents()
		elif self.id_map[menu_id] == "Resume All":
			client.core.resume_all_torrents()


class DelugeSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties").endswith ("deluge.desktop"):
			self.items[pathtoitem] = DelugeItem(self, pathtoitem)

delugesink = DelugeSink()

def cleanup ():
	delugesink.dispose ()

if __name__ == "__main__":
	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))
	reactor.run()
	
