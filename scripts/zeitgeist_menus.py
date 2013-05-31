#!/usr/bin/env python

#  
#  Copyright (C) 2009 Jason Smith, Seif Lotfy, Robert Dyer
#                2010 Rico Tzschichholz
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
import sys
import urllib
import os
import subprocess
import gio
import threading

home = "file://" + os.path.expanduser("~")

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from zeitgeist.client import ZeitgeistClient
	from zeitgeist.datamodel import Event, Subject, Interpretation, Manifestation, StorageState, TimeRange
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	exit()

try:
	CLIENT = ZeitgeistClient()
	version = [int(x) for x in CLIENT.get_version()]
	MIN_VERSION = [0, 4, 0, 0]
	if version < MIN_VERSION:
		print "PLEASE USE ZEITGEIST 0.4.0 or above"
		exit()
		

except RuntimeError, e:
	print "Unable to connect to Zeitgeist, won't send events. Reason: '%s'" %e
	exit()
	
class ZGItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		self.monitor = None 
		self.recent = []
		self.most = []
		self.ids = {}

		self.has_uri = True
		self.uri = self.iface.Get(DOCKITEM_IFACE, "Uri", dbus_interface="org.freedesktop.DBus.Properties")
		if not self.uri:
			self.has_uri = False
			self.uri = self.iface.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties")
			self.uri = 'application://%s' % self.uri[self.uri.rfind('/')+1:]

		self.app_info = None
		app_uri = self.iface.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties")
		apps = gio.app_info_get_all()
		app = None
		t_app = app_uri.split("/")[-1].replace(".desktop", "")
		if t_app:
			for app in apps:
				if t_app in app.get_executable():
					self.app_info = app
					break
		self.update_entries()
	
	def _get_base_template(self):
		base_template = Event()
		if self.has_uri:
			subj = Subject()
			subj.set_uri(self.uri+"/*")
			base_template.set_subjects([subj])
		else:
			base_template.set_actor(self.uri)
		return base_template
	
	def dispose(self):
		if self.monitor:
			CLIENT.remove_monitor(self.monitor)
		DockManagerItem.dispose(self)
	
	def update_entries(self, x=None, y=None, z=None):
		self.recent = []
		self.most = []

		if not self.uri:
			return
		
		def reformat_strings():
			titles = {}
			for r in self.recent:
				if not r[1] in titles:
					titles[r[1]] = []
				titles[r[1]].append(r)
			for m in self.most:
				if not m[1] in titles:
					titles[m[1]] = []
				titles[m[1]].append(m)
			for t in titles:
				if len(titles[t]) > 1:
					for l in titles[t]:
						for i, r in enumerate(self.recent):	
							if l == r:
								self.recent[i][1] = r[1] + " (" + r[0].replace(home, "~") + ")"
								break
						for i, r in enumerate(self.most):	
							if l == r:
								self.most[i][1] = r[1] + " (" + r[0].replace(home, "~") + ")"
								break
						
		def exists(uri):
		 	return uri.startswith("note://") or os.path.exists(urllib.unquote(str(uri[7:])))
		 
		def handle_most(results):
			self.most = []
			for event in results:
				if exists(event.subjects[0].uri):
					self.most.append([event.subjects[0].uri, event.subjects[0].text])
				if len(self.most) >= 5:
					break
			reformat_strings()
			self.update_menu()
			
			if not self.monitor:
				self.monitor = CLIENT.install_monitor(TimeRange.always(), [template], self.update_entries, self.update_entries)
				
		def handle_recent(results):
			self.recent = []
			for event in results:
				if exists(event.subjects[0].uri):
					self.recent.append([event.subjects[0].uri, event.subjects[0].text])
					subj = Subject()
					subj.uri = "!"+event.subjects[0].uri
					template.subjects.append(subj)
				if len(self.recent) >= 5:
					break
			CLIENT.find_events_for_templates([template], handle_most, num_events = 1000, result_type = 4)
		 
		template = self._get_base_template()
		CLIENT.find_events_for_templates([template], handle_recent, num_events = 1000, result_type = 2)


	def update_menu(self):
		for id in self.ids.keys():
			self.remove_menu_item(id)
		self.ids.clear()
		uris = self.most
		for uri in uris:
			uri, title = uri[0], uri[1]
			icon = self.get_icon(uri)
			self.ids[(self.add_menu_item(title, icon, "Other Popular"))] = uri
		uris = self.recent
		for uri in uris:
			uri, title = uri[0], uri[1]
			icon = self.get_icon(uri)
			self.ids[(self.add_menu_item(title, icon, "Latest"))] = uri
	
	def get_icon(self, uri):
		if uri.startswith("note://"):
			return "tomboy-note"
 		file_ = gio.File(uri)
		info = file_.query_info('standard::icon,thumbnail::path')
		thumbnail_path = info.get_attribute_as_string('thumbnail::path')
		if thumbnail_path:
			return thumbnail_path
		else:
		 	icon = info.get_icon() 
		 	icon_path = None
		 	if isinstance(icon, gio.ThemedIcon): 
				icon_path  = icon.get_names()[0]
				#FIXME Handle the list of icons 
				# Docky supports a list of icons separated by ";;"
				#icon_path  = ";;".join(icon.get_names())
			elif isinstance(icon, gio.FileIcon): 
				icon_path = icon.get_file().get_path()
			return icon_path
		
	def menu_pressed(self, menu_id):
		if menu_id in self.ids.keys():
			if self.app_info:
				self.app_info.launch([gio.File(self.ids[menu_id])])	
			else:
				subprocess.Popen(['xdg-open', self.ids[menu_id]])

class ZGSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "Uri", dbus_interface="org.freedesktop.DBus.Properties") != "" or item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties") != "":
			self.items[pathtoitem] = ZGItem(self, pathtoitem)

zgsink = ZGSink()

def cleanup ():
	zgsink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)
	atexit.register (cleanup)
	signal(SIGTERM, lambda signum, stack_frame: exit(1))
	while mainloop.is_running():
		mainloop.run()
