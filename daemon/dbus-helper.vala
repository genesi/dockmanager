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

namespace DockManager
{
  public class DBusWatcher: GLib.Object
  {
    private static DBusWatcher? instance = null;
    public static unowned DBusWatcher get_default ()
    {
      if (instance == null)
      {
        instance = new DBusWatcher ();
      }
      return instance;
    }

    [Signal (detailed=true)]
    public signal void name_appeared (string name);
    [Signal (detailed=true)]
    public signal void name_disappeared (string name);

    private HashTable<string, int> owned_names;
    private dynamic DBus.Object bus_object;
    private Regex unnamed_bus_object;

    private DBusWatcher ()
    {
    }

    construct
    {
      owned_names = new HashTable<string, int> (str_hash, str_equal);

      var connection = DBus.Bus.get (DBus.BusType.SESSION);
      bus_object = connection.get_object ("org.freedesktop.DBus",
                                          "/org/freedesktop/DBus",
                                          "org.freedesktop.DBus");

      bus_object.NameOwnerChanged += this.name_owner_changed;

      unnamed_bus_object = new Regex ("^:\\d+.\\d+$");
      string[] all_names = bus_object.list_names ();
      foreach (var s in all_names)
      {
        if (unnamed_bus_object.match (s) == false)
        {
          owned_names.insert (s, 1);
        }
      }
    }

    private void name_owner_changed (DBus.Object sender, string name,
                                     string old_owner, string new_owner)
    {
      if (unnamed_bus_object.match (name) == false)
      {
        if (new_owner == "")
        {
          // disappeared
          owned_names.replace (name, 0);
          if (Quark.try_string (name) != 0)
          {
            Signal.emit_by_name (this,
                                 "name-disappeared::%s".printf (name),
                                 name);
          }
          else
          {
            name_disappeared (name);
          }
        }
        else if (old_owner == "")
        {
          // appeared
          owned_names.replace (name, 1);
          if (Quark.try_string (name) != 0)
          {
            Signal.emit_by_name (this,
                                 "name-appeared::%s".printf (name),
                                 name);
          }
          else
          {
            name_appeared (name);
          }
        }
      }
    }

    public bool name_has_owner (string name)
    {
      return owned_names.lookup (name) != 0;
    }
  }
}

