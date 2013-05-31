#!/usr/bin/env python

#  
#  Copyright (C) 2010 Dan Korostelev, Rico Tzschichholz, Robert Dyer, Michal Hruby
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

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from signal import signal, SIGTERM
	from sys import exit
	import urllib2
	import json
except ImportError, e:
	print e
	exit()

transmissionbus = "com.transmissionbt.Transmission"
transmissionrpcurl = "http://localhost:9091/transmission/rpc"
UPDATE_DELAY = 3000 # 3 secs


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


class TransmissionItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.timer = 0
		
		self.down_speed = ""
		self.up_speed = ""
		self.progress = -1
		
		self.bus.add_signal_receiver(self.name_owner_changed_cb,
		                             dbus_interface='org.freedesktop.DBus',
		                             signal_name='NameOwnerChanged',
		                             arg0=transmissionbus)
		
		self.start_polling()

	def name_owner_changed_cb(self, name, old_owner, new_owner):
		if new_owner:
			# transmission started, resume polling
			self.start_polling()
		else:
			# transmission stopped, stop polling
			self.stop_polling()

	def start_polling(self):
		if not self.timer > 0:
			self.timer = gobject.timeout_add(UPDATE_DELAY, self.refresh_item)
			self.refresh_item()

	def stop_polling(self):
		if self.timer > 0:
			gobject.source_remove(self.timer)
			self.timer = 0
		self.reset_badge()
		self.reset_progress()
		self.reset_tooltip()

	def refresh_item(self):
		try:
			self.update_stats()
			
			self.set_progress(self.progress)
			
			if len(self.down_speed) > 0:
				self.set_badge(self.down_speed)
			else:
				self.reset_badge()
			
			if len(self.down_speed) > 0 and len(self.up_speed) > 0:
				self.set_tooltip("Transmission - " + self.down_speed + "B/s down " + self.up_speed + "B/s up")
			elif len(self.down_speed) > 0:
				self.set_tooltip("Transmission - " + self.down_speed + "B/s down")
			elif len(self.up_speed) > 0:
				self.set_tooltip("Transmission - " + self.up_speed + "B/s up")
		except Exception as e:
			return False
		return True
	
	def get_transmission_data(self, request):
		result = None
		
		for i in range(2): # first try can be getting session id
			try:
				response = urllib2.urlopen(request)
				result = json.load(response)
				break # if no error, we don't need second try
			except urllib2.HTTPError, e:
				result = None
				if e.code == 409 and 'X-Transmission-Session-Id' in e.headers:
					request.add_header('X-Transmission-Session-Id', e.headers['X-Transmission-Session-Id'])
		
		return result
	
	def update_stats(self):
		try:
			# update the speeds
			request = urllib2.Request(transmissionrpcurl)
			req_info = {'method':'session-stats'}
			request.add_data(json.dumps(req_info))
			result = self.get_transmission_data(request)
			
			self.down_speed = ""
			self.up_speed = ""
			if result:
				speed = result['arguments']['downloadSpeed']
				if speed:
					self.down_speed = bytes2ratestr(speed)
				speed = result['arguments']['uploadSpeed']
				if speed:
					self.up_speed = bytes2ratestr(speed)
			
			# update the progress
			request = urllib2.Request(transmissionrpcurl)
			req_info = {'method':'torrent-get', 'arguments':{'fields':['percentDone', 'status']}}
			request.add_data(json.dumps(req_info))
			result = self.get_transmission_data(request)
			
			self.progress = -1
			if result:
				percents = result['arguments']['torrents']
				total_percent = num_download = 0
				TR_STATUS_DOWNLOADING = 4
				
				for torrent in percents:
					if torrent['status'] & TR_STATUS_DOWNLOADING != 0:
						num_download += 1
						total_percent += torrent['percentDone']
				
				if (num_download > 0):
					self.progress = int(total_percent / num_download * 100)
		except Exception as e:
			self.stop_polling()


class TransmissionSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		desktop_file = item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties")
		if desktop_file.endswith("transmission.desktop") or desktop_file.endswith("transmission-gtk.desktop"):
			self.items[pathtoitem] = TransmissionItem(self, pathtoitem)

transmissionsink = TransmissionSink()

def cleanup ():
	transmissionsink.dispose ()

if __name__ == '__main__':
	mainloop = gobject.MainLoop(is_running=True)
	
	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))
	
	mainloop.run()
