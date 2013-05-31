#!/usr/bin/env python

#  
#  Copyright (C) 2010 Erigami Scholey-Fuller
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
import sys
import os
import time
import dbus
import math

try:
    from dockmanager.dockmanager import DockManagerItem, DockManagerSink, DOCKITEM_IFACE
    from signal import signal, SIGTERM
    from sys import exit
except ImportError, e:
    print `e`
    exit()

break_names = {
    'micro_pause' : "Micro break",
    'rest_break' : 'Rest break',
    'daily_limit' : 'Daily limit'
}

class Workrave:
    """Interface to Workrave."""

    def connect(self, bus):
        obj = bus.get_object("org.workrave.Workrave",
                "/org/workrave/Workrave/Core")
        self.workrave = dbus.Interface(obj, "org.workrave.CoreInterface")
        self.config = dbus.Interface(obj, "org.workrave.ConfigInterface")


    def findNextEnd(self):
        """Find the next timer to go off.

        Returns an array of tuples. Each typle consists of 
        (seconds-until-timer-ends, length-of-timer, time-timer-ends, name-of-timer), 
        where the timer is the next timer scheduled to end.

        If there are no ticking timers, an empty array is returned. 
        """
        # Pick a really large number for the next timer
        remaining = 2 ** 18

        toReturn = []
        for (timerName, configName) in [['microbreak', 'micro_pause'], ['restbreak', 'rest_break'], ['dailylimit', 'daily_limit']]:
            if not self.workrave.IsTimerRunning(timerName):
                continue
            (length, found) = self.config.GetInt('timers/%s/limit' % configName)
            if not found:
                continue

            elapsed = self.workrave.GetTimerElapsed(timerName)
            r = length - elapsed

            tuple = (r, length, r + time.time(), configName)
            toReturn.append(tuple)

        def c(a, b):
            return cmp(a[0], b[0])

        toReturn.sort(c)

        return toReturn


class WorkraveWatcher:
    """Responsible for monitoring Workrave and updating the UI."""

    def __init__(self):
        self.wr = Workrave()
        self.dock_item = None
        self.workrave_state = None
        self.breaks = []
        self.timers = []


    def on_service_change(self, bus, conn):
        if "" == conn:
            # Workrave has gone away
            self.workrave_state = None
            self.breaks = []
            
            for timer in self.timers:
                gobject.source_remove(timer)

            self.timers = []

            return

        # A new workrave is here to play with us
        try:
            self.wr.connect(bus)
        except dbus.exceptions.DBusException, e:
            return

        self.wr.workrave.connect_to_signal('MicrobreakChanged', 
                lambda x: self.__state_change('micro', x))
        self.wr.workrave.connect_to_signal('RestbreakChanged', 
                lambda x: self.__state_change('rest', x))
        self.wr.workrave.connect_to_signal('DailylimitChanged', 
                lambda x: self.__state_change('daily', x))

        self.timers.append(gobject.timeout_add(5000, self.__poll_workrave))
        self.timers.append(gobject.timeout_add(1000, self.__update_ui))


    def __state_change(self, timer, progress):
        self.workrave_state = progress
        self.__poll_workrave()


    def __poll_workrave(self):
        self.breaks = self.wr.findNextEnd()

        return True

    def __update_ui(self):
        message = ""
        progress = 0
        if self.workrave_state == 'break':
            message = 'Break'
        else:
            next_break = 0
            duration = 0
            if len(self.breaks) > 0:
                next_break = self.breaks[0][2]
                duration = self.breaks[0][1]

            if next_break <= 0:
                message = "(pause)"
            else:
                rem = next_break - time.time()
                message = self.__humanize_time(rem)
                if rem < 0:
                    progress = 100
                else:
                    progress = 100 - int(100 * (float(rem) / float(duration)))

        if self.dock_item:
            self.dock_item.set_message(message)
            self.dock_item.set_progress(progress)
            self.dock_item.set_tooltip(self.__calculate_tooltip())

        return True

    def __calculate_tooltip(self):
        toReturn = ''

        for timer in self.breaks:
            if len(toReturn) > 0:
                toReturn = toReturn + ",  "

            secondsLeft = int(timer[2] - time.time())
            msg = self.__humanize_time(secondsLeft, False)
            toReturn = toReturn + ("%s in %s" % (break_names[timer[3]], msg))

        if len(toReturn) == 0:
            toReturn = 'Workrave'

        toReturn = toReturn + "  "

        return toReturn
            

    def __humanize_time(self, rem, hide_seconds=True):
        if rem < 0:
            minutes = -1 * math.ceil(float(rem) / 60)
            seconds = (-1 * rem) % 60
            message = "-%i:%02i" % (minutes, seconds)
        else:
            minutes = int(rem / 60)
            seconds = rem % 60
            if hide_seconds and minutes >= 5:
                message = "%im" % minutes
            else:
                message = "%i:%02i" % (minutes, seconds)
        
        return message
        
    def register_dock_item(self, item):
        self.dock_item = item


    def dispose(self):
        if self.dock_item:
            self.dock_item.set_message("")


    def set_item(self, item):
        """Called to set the item we're showing in the dock"""
        self.dock_item = item

watcher = WorkraveWatcher()


class WorkraveItem(DockManagerItem):

    def __init__(self, sink, path):
        DockManagerItem.__init__(self, sink, path)

        # Initialize our dbus interface
        self.__dbus = dbus.SessionBus()

        watcher.set_item(self)
        #self.add_menu_item("Preferences", "preferences", "Preferences")

    def set_message(self, msg):
        self.iface.UpdateDockItem({"message": msg})

    def menu_pressed(self, menu_id):
        pass


class WorkraveSink(DockManagerSink):
    def item_path_found(self, pathtoitem, item):
        path = item.Get(DOCKITEM_IFACE, "DesktopFile", dbus_interface="org.freedesktop.DBus.Properties")
        if path.endswith("workrave.desktop"):
            self.items[pathtoitem] = WorkraveItem(self, pathtoitem)
            watcher.register_dock_item(self.items[pathtoitem])
                         

def cleanup():
    watcher.dispose()
    sink.dispose()

sink = WorkraveSink()


if __name__ == "__main__":
    bus = dbus.SessionBus()
    bus.watch_name_owner("org.workrave.Workrave", lambda x: watcher.on_service_change(bus, x))

    mainloop = gobject.MainLoop(is_running=True)
     
    atexit.register(cleanup)
    signal(SIGTERM, lambda signum, stack_frame: exit(1))

    mainloop.run()
