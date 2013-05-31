#!/usr/bin/env python
# -.- coding: utf-8 -.-

#
# Copyright (c) 2009 Seif Lotfy, Siegfried Gevatter
# Copyright (c) 2010 Robert Dyer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import gobject
import sys
import urllib
import datetime
import time
import os
import gtk
import gnome.ui
import atexit

try:
	from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
	from zeitgeist.client import ZeitgeistClient
	from zeitgeist.datamodel import Event, Subject, Interpretation, Manifestation, StorageState
	from signal import signal, SIGTERM
	from sys import exit
except ImportError, e:
	exit()

try:
	CLIENT = ZeitgeistClient()
	version = [int(x) for x in CLIENT.get_version()]
	MIN_VERSION = [0, 3, 1, 0]
	if version < MIN_VERSION:
		print "PLEASE USE ZEITGEIST 0.3.1 or above"
		exit()

except RuntimeError, e:
	print "Unable to connect to Zeitgeist, won't send events. Reason: '%s'" %e
	exit()

INTERPRETATION = {
		"http://zeitgeist-project.com/schema/1.0/core#VisitEvent":"OPENED",
		"http://zeitgeist-project.com/schema/1.0/core#ModifyEvent":"SAVED",
		"http://zeitgeist-project.com/schema/1.0/core#CreateEvent":"CREATED"
		}

class LaunchManager:
    """
    A program lauching utility which handles opening a URI or executing a
    program or .desktop launcher, handling variable expansion in the Exec
    string.

    Adds the launched URI or launcher to the ~/.recently-used log. Sets a
    DESKTOP_STARTUP_ID environment variable containing useful information such
    as the URI which caused the program execution and a timestamp.

    See the startup notification spec for more information on
    DESKTOP_STARTUP_IDs.
    """
    
    def __init__(self):
        self.recent_model = None

    def _get_recent_model(self):
        # FIXME: This avoids import cycles
        if not self.recent_model:
            import zeitgeist_recent
            self.recent_model = zeitgeist_recent.recent_model
        return self.recent_model
    
    def launch_uri(self, uri, mimetype = None):
        assert uri, "Must specify URI to launch"
    
        child = os.fork()
        if not child:
            # Inside forked child
            os.setsid()
            os.environ['zeitgeist_LAUNCHER'] = uri
            os.environ['DESKTOP_STARTUP_ID'] = self.make_startup_id(uri)
            os.spawnlp(os.P_NOWAIT, "gnome-open", "gnome-open", uri)
            os._exit(0)
        else:
            os.wait()
            if not mimetype:
                mimetype = "application/octet-stream"
            try:
                # Use XDG to lookup mime type based on file name.
                # gtk_recent_manager_add_full requires it.
                import xdg.Mime
                mimetype = xdg.Mime.get_type_by_name(uri)
                if mimetype:
                    mimetype = str(mimetype)
                return mimetype
            except (ImportError, NameError):
                # No mimetype found for URI: %s
                pass
        return child
    
    def get_local_path(self, uri):
        scheme, path = urllib.splittype(uri)
        if scheme == None:
            return uri
        elif scheme == "file":
            path = urllib.url2pathname(path)
            if path[:3] == "///":
                path = path[2:]
            return path
        return None
    
    def launch_command_with_uris(self, command, uri_list, launcher_uri = None):
        if command.rfind("%U") > -1:
            uri_str = ""
            for uri in uri_list:
                uri_str = uri_str + " " + uri
                return self.launch_command(command.replace("%U", uri_str), launcher_uri)
        elif command.rfind("%F") > -1:
            file_str = ""
            for uri in uri_list:
                uri = self.get_local_path(self, uri)
                if uri:
                    file_str = file_str + " " + uri
                else:
                    # Command does not support non-file URLs
                    pass
            return self.launch_command(command.replace("%F", file_str), launcher_uri)
        elif command.rfind("%u") > -1:
            startup_ids = []
            for uri in uri_list:
                startup_ids.append(self.launch_command(command.replace("%u", uri), launcher_uri))
            else:
                return self.launch_command(command.replace("%u", ""), launcher_uri)
            return startup_ids
        elif command.rfind("%f") > -1:
            startup_ids = []
            for uri in uri_list:
                uri = self.get_local_path(self, uri)
                if uri:
                    startup_ids.append(self.launch_command(command.replace("%f", uri),
                                                           launcher_uri))
                else:
                    #print " !!! Command does not support non-file URLs: ", command
                    pass
            else:
                return self.launch_command(command.replace("%f", ""), launcher_uri)
            return startup_ids
        else:
            return self.launch_command(command, launcher_uri)
    
    def make_startup_id(self, key, ev_time = None):
        if not ev_time:
            ev_time = gtk.get_current_event_time()
        if not key:
            return "zeitgeist_TIME%d" % ev_time
        else:
            return "zeitgeist:%s_TIME%d" % (key, ev_time)

    def parse_startup_id(self, id):
        if id and id.startswith("zeitgeist:"):
            try:
                uri = id[len("zeitgeist:"):id.rfind("_TIME")]
                timestamp = id[id.rfind("_TIME") + len("_TIME"):]
                return (uri, timestamp)
            except IndexError:
                pass
        return (None, None)

    def launch_command(self, command, launcher_uri = None):
        startup_id = self.make_startup_id(launcher_uri)
        child = os.fork()
        if not child:
            # Inside forked child
            os.setsid()
            os.environ['DESKTOP_STARTUP_ID'] = startup_id
            if launcher_uri:
                os.environ['zeitgeist_LAUNCHER'] = launcher_uri
            os.system(command)
            os._exit(0)
        else:
            os.wait()
           
            return (child, startup_id)

class IconFactory():
    """
    Icon lookup swiss-army knife (from menutreemodel.py)
    """
    
    def __init__(self):
        self.icon_dict={}
    
    def load_icon_from_path(self, icon_path, icon_size=None):
        try:
            if icon_size:
                icon = gtk.gdk.pixbuf_new_from_file_at_size(icon_path,
                    int(icon_size), int(icon_size))
                return icon
            else:
                return gtk.gdk.pixbuf_new_from_file(icon_path)
        except Exception:
            pass
        return None
    
    def load_icon_from_data_dirs(self, icon_value, icon_size=None):
        data_dirs = None
        if os.environ.has_key("XDG_DATA_DIRS"):
            data_dirs = os.environ["XDG_DATA_DIRS"]
        if not data_dirs:
            data_dirs = "/usr/local/share/:/usr/share/"

        for data_dir in data_dirs.split(":"):
            retval = self.load_icon_from_path(os.path.join(data_dir, "pixmaps", icon_value),
                                              icon_size)
            if retval:
                return retval
            
            retval = self.load_icon_from_path(os.path.join(data_dir, "icons", icon_value),
                                              icon_size)
            if retval:
                return retval
        return None
    
    def transparentize(self, pixbuf, percent):
        pixbuf = pixbuf.add_alpha(False, '0', '0', '0')
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[3] = min(int(pix[3]), 255 - (percent * 0.01 * 255))
        return pixbuf
    
    def greyscale(self, pixbuf):
        pixbuf = pixbuf.copy()
        for row in pixbuf.get_pixels_array():
            for pix in row:
                pix[0] = pix[1] = pix[2] = (int(pix[0]) + int(pix[1]) + int(pix[2])) / 3
        return pixbuf
    
    def load_icon(self, icon_value, icon_size, force_size=True, cache=True):
        if not self.icon_dict.has_key(str(icon_value)+str(icon_size)) or not cache:
            try:
                if isinstance(icon_value, gtk.gdk.Pixbuf):
                    return icon_value
                elif os.path.isabs(icon_value):
                    icon = self.load_icon_from_path(icon_value, icon_size)
                    if icon:
                        return icon
                    icon_name = os.path.basename(icon_value)
                else:
                    icon_name = icon_value
                
                if icon_name.endswith(".png"):
                    icon_name = icon_name[:-len(".png")]
                elif icon_name.endswith(".xpm"):
                    icon_name = icon_name[:-len(".xpm")]
                elif icon_name.endswith(".svg"):
                    icon_name = icon_name[:-len(".svg")]
                
                icon = None
                info = icon_theme.lookup_icon(icon_name, icon_size, gtk.ICON_LOOKUP_USE_BUILTIN)
                if info:
                    if icon_name.startswith("gtk-"):
                        icon = info.load_icon()
                    elif info.get_filename():
                        icon = self.load_icon_from_path(info.get_filename(), icon_size)
                else:
                    icon = self.load_icon_from_data_dirs(icon_value, icon_size) 
                
                if cache:
                    self.icon_dict[str(icon_value)+str(icon_size)] = icon
                return icon
            except Exception:
                self.icon_dict[str(icon_value)+str(icon_size)] = None
                return None
        else:
            return self.icon_dict[str(icon_value)+str(icon_size)]
    
    def load_image(self, icon_value, icon_size, force_size=True):
        pixbuf = self.load_icon(icon_value, icon_size, force_size)
        img = gtk.Image()
        img.set_from_pixbuf(pixbuf)
        img.show()
        return img

    def make_icon_frame(self, thumb, icon_size = None, blend = False):
        border = 1

        mythumb = gtk.gdk.Pixbuf(thumb.get_colorspace(),
                                 True,
                                 thumb.get_bits_per_sample(),
                                 thumb.get_width(),
                                 thumb.get_height())
        mythumb.fill(0x00000080) # black, 50% transparent
        if blend:
            thumb.composite(mythumb, 0.5, 0.5,
                            thumb.get_width(), thumb.get_height(),
                            0.5, 0.5,
                            0.5, 0.5,
                            gtk.gdk.INTERP_NEAREST,
                            256)
        thumb.copy_area(border, border,
                        thumb.get_width() - (border * 2), thumb.get_height() - (border * 2),
                        mythumb,
                        border, border)
        return mythumb
    
    
class Thumbnailer:
    
    def __init__(self):
        self.icon_dict={}

    def get_icon(self, subject, icon_size, timestamp = 0):
        
        uri = subject.uri
        if not self.icon_dict.get(uri+str(icon_size)):
            cached_icon = self._lookup_or_make_thumb(uri, subject.mimetype,
                icon_size, timestamp)
            self.icon_dict[uri+str(icon_size)] = cached_icon
        
        return self.icon_dict[uri+str(icon_size)]

    def _lookup_or_make_thumb(self, uri, mimetype, icon_size, timestamp):
        icon_name, icon_type = \
                   gnome.ui.icon_lookup(icon_theme, thumb_factory, uri, mimetype, 0)
        try:
            if icon_type == gnome.ui.ICON_LOOKUP_RESULT_FLAGS_THUMBNAIL or \
                   thumb_factory.has_valid_failed_thumbnail(uri,int(timestamp)):
                # Use existing thumbnail
                thumb = icon_factory.load_icon(icon_name, icon_size)
            elif self._is_local_uri(uri):
                # Generate a thumbnail for local files only
                thumb = thumb_factory.generate_thumbnail(uri, mimetype)
                thumb_factory.save_thumbnail(thumb, uri, timestamp)

            if thumb:
                thumb = icon_factory.make_icon_frame(thumb, icon_size)
                return thumb
            
        except Exception:
            pass

        return icon_factory.load_icon(icon_name, icon_size)

    def _is_local_uri(self, uri):
        # NOTE: gnomevfs.URI.is_local seems to hang for some URIs (e.g. ssh
        #        or http).  So look in a list of local schemes which comes
        #        directly from gnome_vfs_uri_is_local_scheme.
        scheme, path = urllib.splittype(self.get_uri() or "")
        return not scheme or scheme in ("file", "help", "ghelp", "gnome-help", "trash",
                                        "man", "info", "hardware", "search", "pipe",
                                        "gnome-trash")

class CellRendererPixbuf(gtk.CellRendererPixbuf):
    
    __gsignals__ = {
        'toggled': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
        (gobject.TYPE_STRING,))
    }
    def __init__(self):
        gtk.CellRendererPixbuf.__init__(self)
        self.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)
    
    def do_activate(self, event, widget, path, background_area, cell_area, flags):
        model = widget.get_model()
        self.emit("toggled",path)

icon_theme = gtk.icon_theme_get_default()
icon_factory = IconFactory()
thumbnailer = Thumbnailer()
thumb_factory = gnome.ui.ThumbnailFactory("normal")
launcher = LaunchManager()


from zeitgeist.datamodel import Event, Subject, Interpretation, Manifestation, StorageState

class Window(gtk.Window):
	def __init__(self, CLIENT):
		gtk.Window.__init__(self)
		self.view = DataIconView()
		scroll = gtk.ScrolledWindow()
		scroll.add_with_viewport(self.view)
		self.add(scroll)
		scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._zg = CLIENT
		self.set_size_request(600,480)
		self.show_all()

	def load_events(self, start=0, end=0, actor=None):
		self.set_title("Journal for "+actor)
		def exists(uri):
			return not uri.startswith("file://") or os.path.exists(urllib.unquote(str(uri[7:])))

		def _handle_find_events(ids):
			self._zg.get_events(ids, _handle_get_events)

		def _handle_get_events(events):
			uris = []
			for event in events:
				for subject in event.subjects:
					if exists(subject.uri):
						self.view.append_object(event)
		
		event = Event()
		event.set_actor(actor)
		self._zg.find_events_for_templates([event],_handle_get_events, [start, end], StorageState.Any, 0, 4) 


class DataIconView(gtk.TreeView):
	def __init__(self):
		gtk.TreeView.__init__(self)
		self.store = gtk.TreeStore(gtk.gdk.Pixbuf,
					str,	#TIME
					str,	#INTERPRETATION
					str,	#Subject_TEXT
					gobject.TYPE_PYOBJECT
					)

		# Icon 
		icon_cell = gtk.CellRendererPixbuf()
		icon_cell.set_property("yalign", 0.5)
		icon_column = gtk.TreeViewColumn("Icon",icon_cell,pixbuf=0)
		
		time_cell = gtk.CellRendererText()
		time_column = gtk.TreeViewColumn("Time", time_cell, markup=1)
				
		interp_cell = gtk.CellRendererText()
		interp_column = gtk.TreeViewColumn("Interpretation", interp_cell, markup=2)
		
		subject_cell = gtk.CellRendererText()
		subject_column = gtk.TreeViewColumn("Subject", subject_cell, markup=3)
		
		self.append_column(time_column)
		self.append_column(icon_column)
		self.append_column(subject_column)
		self.append_column(interp_column)
		self.set_model(self.store)

		self.set_headers_visible(False)
		self.iter = {"uri":None, "iter":None}

	def clear(self):
		self.store.clear()

	def append_object(self, event):

		icon = thumbnailer.get_icon(event.subjects[0], 32)
		date = int(event.timestamp)/1000
		date = datetime.datetime.fromtimestamp(date).strftime("%H:%M:%S		%A, %D") 

		iterator = None
		if self.iter["uri"] == event.subjects[0].uri:
			self.store.append(self.iter["iter"], 
						[icon,
						date,
						INTERPRETATION[event.interpretation],
						event.subjects[0].text,
						event])
		else:
			iterator = None
			self.iter["uri"] = event.subjects[0].uri
			self.iter["iter"] = self.store.append(None, [icon,
								date,
								INTERPRETATION[event.interpretation],
								event.subjects[0].text,
								event])


class JournalItem(DockManagerItem):
	def __init__(self, sink, path):
		DockManagerItem.__init__(self, sink, path)
		menu_id = self.add_menu_item("Journal", "document-open-recent")
		self.id_map[menu_id] = "Journal"
		self.uri = self.iface.Get(DOCKITEM_IFACE, "Uri", dbus_interface="org.freedesktop.DBus.Properties")
		if not self.uri:
			self.uri = self.iface.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties")
			self.uri = 'application://%s' % self.uri[self.uri.rfind('/')+1:]

	def menu_pressed(self, menu_id):
		if self.id_map[menu_id] == "Journal":
			window = Window(CLIENT)
			window.load_events(0, time.time() * 1000, self.uri)


class JournalSink(DockManagerSink):
	def item_path_found(self, pathtoitem, item):
		if item.Get(DOCKITEM_IFACE, "Uri", dbus_interface="org.freedesktop.DBus.Properties") or item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties"):
			self.items[pathtoitem] = JournalItem(self, pathtoitem)


zgjournalsink = JournalSink()

def cleanup ():
	zgjournalsink.dispose ()

if __name__ == "__main__":
	mainloop = gobject.MainLoop(is_running=True)

	atexit.register (cleanup)
	
	signal(SIGTERM, lambda signum, stack_frame: exit(1))

	while mainloop.is_running():
	    mainloop.run()
