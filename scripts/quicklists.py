#!/usr/bin/env python

#  
#  Copyright (C) 2010 Eugeny Pankov
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

import atexit
import gobject
import glib
import gio
import locale
import sys
import os
import subprocess
from ConfigParser import ConfigParser
from signal import signal, SIGTERM
from sys import exit

try:
    from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
except ImportError, e:
    print e
    exit()

desktop_cache = {}


class QuickListItem(DockManagerItem):
    def __init__(self, sink, name, path):
        global desktop_cache
        DockManagerItem.__init__(self, sink, path)

        if name in desktop_cache:
            cfg = desktop_cache[name]
        else:
            cfg = ConfigParser()
            cfg.read(name)
            desktop_cache[name] = cfg
            
        try:
            icon = cfg.get('Desktop Entry', 'Icon')
        except:
            icon = os.path.split(name)[1].split('.')[0]

        self.items = {}
        
        lc = locale.getdefaultlocale()[0]
        names = [
            'Name[%s]'%lc,
            'Name[%s]'%lc.split('_')[0],
            'Name',
        ]
        
        for section in cfg.sections():
            if section.endswith('Shortcut Group'):
                name = None
                for n in names:
                    try:
                        name = cfg.get(section, n)
                        break
                    except:
                        pass
                        
                self.add_menu_item(
                    name,
                    icon, 
                    'Quicklist',
                )
                self.items[name] = cfg.get(section, 'Exec')

    def menu_pressed(self, menu_id):
        gio.AppInfo(self.items[self.id_map[menu_id]]).launch()
	      
	        
class QuickListSink(DockManagerSink):
    def item_path_found(self, pathtoitem, item):
        name = str(item.Get(DOCKITEM_IFACE, 'DesktopFile', dbus_interface='org.freedesktop.DBus.Properties'))
        if name:
            self.items[pathtoitem] = QuickListItem(self, name, pathtoitem)


sink = QuickListSink()

def cleanup ():
    sink.dispose()

if __name__ == '__main__':
    mainloop = gobject.MainLoop(is_running=True)

    atexit.register (cleanup)
    signal(SIGTERM, lambda signum, stack_frame: exit(1))

    mainloop.run()
