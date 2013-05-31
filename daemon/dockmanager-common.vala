/*
 * Copyright (C) 2010 Michal Hruby <michal.mhr@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.
 *
 * Authored by Michal Hruby <michal.mhr@gmail.com>
 *
 */

using DBus;
using DesktopAgnostic;

namespace DockManager
{
  const string DBUS_UNIQUE_NAME = "net.launchpad.DockManager.Daemon";
  const string DBUS_INTERFACE_NAME = "net.launchpad.DockManager.Daemon";
  const string DBUS_OBJECT_PATH_NAME = "/net/launchpad/DockManager/Daemon";

  [DBus (name = "net.launchpad.DockManager.Daemon")]
  public interface DaemonInterface: GLib.Object
  {
    public abstract HelperInfo[] get_all_helpers () throws DBus.Error;
    public abstract void enable_helper (string path) throws DBus.Error;
    public abstract void disable_helper (string path) throws DBus.Error;
    public abstract void restart_all () throws DBus.Error;
    public async abstract bool install_helper (string filename) throws DBus.Error;
    public abstract void show_preferences () throws DBus.Error;
    public abstract void embed_preferences (int64 xid,
                                            HashTable<string, Value?> hints)
                                            throws DBus.Error;

    public signal void helper_list_changed ();
    public signal void helper_state_changed (string path,
                                             bool enabled, bool running);
  }

  public struct HelperInfo
  {
    string path;
    string? name;
    string? description;
    string? icon_name;
    string? app_name;
    string? dbus_name;
    bool app_available;
    bool enabled;
    bool running;
  }
}

