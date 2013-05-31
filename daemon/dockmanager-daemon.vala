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
  const string GROUP_NAME = "DockmanagerHelper";

  private struct HelperProcessInfo
  {
    int pid;
    uint kill_timer_id;
    ulong dbus_appear_id;
    ulong dbus_disappear_id;
  }

  class HelperDaemon : GLib.Object, DaemonInterface
  {
    private MainLoop main_loop;
    private DBusWatcher watcher;

    private ValueArray _helper_list = new ValueArray (4);
    public unowned ValueArray helper_list
    {
      get
      {
        return _helper_list;
      }
      set
      {
        _helper_list = value.copy ();
      }
    }

    private HashTable<string, HelperProcessInfo?> helper_process_info;
    private List<HelperInfo?> all_scripts;
    private bool dock_running;

    public HelperDaemon ()
    {
      main_loop = new MainLoop ();

      helper_process_info = 
        new HashTable<string, HelperProcessInfo?> (str_hash, str_equal);
      all_scripts = new List<HelperInfo?> ();

      watcher = DBusWatcher.get_default ();
      dock_running = watcher.name_has_owner ("net.launchpad.DockManager");
      watcher.name_appeared["net.launchpad.DockManager"].connect (() =>
      {
        dock_running = true;
        run_helpers ();
      });
      watcher.name_disappeared["net.launchpad.DockManager"].connect (() =>
      {
        dock_running = false;
        kill_all ();
      });
    }

    public override void constructed ()
    {
      string schema_filename = "dockmanager-daemon.schema-ini";
      string schema_full = Build.SCHEMAFILEDIR + "/" + schema_filename;
      Config.Client client = new Config.Client (schema_full);

      try
      {
        client.bind ("DEFAULT", "helper_list",
                     this, "helper-list", false,
                     Config.BindMethod.FALLBACK);
      }
      catch (DesktopAgnostic.Config.Error err)
      {
        warning (err.message);
      }
    }

    public void run ()
    {
      try
      {
        var connection = DBus.Bus.get (DBus.BusType.SESSION);
        dynamic DBus.Object bus =
          connection.get_object ("org.freedesktop.DBus",
                                 "/org/freedesktop/DBus",
                                 "org.freedesktop.DBus");

        uint request_name_result =
          bus.request_name (DBUS_UNIQUE_NAME, (uint) NameFlag.DO_NOT_QUEUE);

        if (request_name_result == RequestNameReply.PRIMARY_OWNER)
        {
          connection.register_object (DBUS_OBJECT_PATH_NAME, this);

          this.init ();
          this.run_helpers ();

          main_loop.run ();
          this.kill_all ();
        }
        else
        {
          error ("Another instance of DockManager daemon is already running!");
        }
      }
      catch (DBus.Error err)
      {
        warning ("%s", err.message);
      }
    }

    private void init ()
    {
      string[] prefixes = 
      {
        Build.PKGDATADIR,
        Environment.get_user_data_dir () + "/dockmanager"
      };

      foreach (unowned string prefix in prefixes)
      {
        string path = prefix + "/scripts";
        string metadata_dir = prefix + "/metadata/";
        var scripts_dir = DesktopAgnostic.VFS.file_new_for_path (path);
        if (!scripts_dir.exists ()) continue;

        foreach (var f in scripts_dir.enumerate_children ())
        {
          var hi = HelperInfo ();
          hi.path = f.path;
          hi.app_available = true; // probably... we'll set it later
          all_scripts.append (hi);
        }

        foreach (unowned HelperInfo? hi in all_scripts)
        {
          string metadata = metadata_dir + Path.get_basename (hi.path) + ".info";
          var metadata_file = DesktopAgnostic.VFS.file_new_for_path (metadata);
          if (!metadata_file.exists ()) continue;

          string contents;
          size_t length;
          metadata_file.load_contents (out contents, out length);

          var keyfile = new KeyFile ();
          try
          {
            keyfile.load_from_data (contents, length, KeyFileFlags.NONE);
          }
          catch (KeyFileError err)
          {
            warning ("Cannot load %s: %s", metadata, err.message);
            continue;
          }

          try
          {
            hi.name = keyfile.get_string (GROUP_NAME, "Name");
            hi.description = keyfile.get_string (GROUP_NAME, "Description");
          }
          catch (KeyFileError err)
          {
            warning ("Required key missing in %s", metadata);
            continue;
          }
          try
          {
            hi.icon_name = keyfile.get_string (GROUP_NAME, "Icon");
          }
          catch (KeyFileError err) { }
          try
          {
            hi.app_name = keyfile.get_string (GROUP_NAME, "AppName");

            hi.app_available =
              Environment.find_program_in_path (hi.app_name) != null;
          }
          catch (GLib.Error err)
          {
            warning ("%s", err.message);
          }
          try
          {
            hi.dbus_name = keyfile.get_string (GROUP_NAME, "DBusName");
          }
          catch (KeyFileError err) { }
        }
      }
    }

    public void run_helpers ()
    {
      foreach (Value v in _helper_list)
      {
        unowned string helper = v.get_string ();
        enable_helper (helper);
      }

      /*
      helper_process_info.@foreach ((k, v) =>
      {
        unowned string key = (string) k;
        unowned HelperProcessInfo? val = (HelperProcessInfo?) v;
        debug ("%s: %d", key, val.pid);
      });
      */
    }

    private int get_helper_pid (string path)
    {
      unowned HelperProcessInfo? hpi = helper_process_info.lookup (path);
      return hpi != null ? hpi.pid : 0;
    }

    private string? get_helper_dbus_name (string path)
    {
      foreach (unowned HelperInfo? hi in all_scripts)
      {
        if (hi.path == path) return hi.dbus_name;
      }
      return null;
    }

    private bool is_helper_enabled (string path)
    {
      foreach (Value v in _helper_list)
      {
        if (v.get_string () == path) return true;
      }

      return false;
    }

    public void enable_helper (string path) throws DBus.Error
    {
      Pid child_pid = 0;
      string[] argv;

      // if the helper is already running we're done
      // FIXME: but what if it's disabled and just waiting to be killed?
      if (get_helper_pid (path) != 0)
      {
        return;
      }

      if (!is_helper_enabled (path))
      {
        Value p = path;
        _helper_list.append (p);
        this.notify_property ("helper-list");
      }

      if (!dock_running)
      {
        helper_state_changed (path, true, false);
        return;
      }

      string? dbus_name = get_helper_dbus_name (path);
      if (dbus_name != null)
      {
        unowned HelperProcessInfo? hpi = update_helper (path);

        if (hpi.dbus_appear_id == 0)
        {
          hpi.dbus_appear_id = SignalFix.connect (
            watcher, "name-appeared::%s".printf (dbus_name), () =>
            {
              enable_helper (path);
            }
          );
        }
        if (hpi.dbus_disappear_id == 0)
        {
          hpi.dbus_disappear_id = SignalFix.connect (
            watcher, "name-disappeared::%s".printf (dbus_name), () =>
            {
              // give it a moment to exit itself and then kill it
              Timeout.add (1000, ()=> { kill_helper (path); return false; });
            }
          );
        }

        if (!watcher.name_has_owner (dbus_name))
        {
          helper_state_changed (path, true, false);
          return;
        }
      }

      try
      {
        Shell.parse_argv (path, out argv);
        var flags = SpawnFlags.DO_NOT_REAP_CHILD | SpawnFlags.SEARCH_PATH;
        Process.spawn_async (null, argv, null, flags, null, out child_pid);
        ChildWatch.add_full (Priority.DEFAULT, child_pid, (pid, status) =>
        {
          debug ("[%d] \"%s\" exitted", pid, Path.get_basename (path));
          unowned HelperProcessInfo? hpi = update_helper (path);
          if (hpi.kill_timer_id != 0)
          {
            Source.remove (hpi.kill_timer_id);
          }
          hpi.pid = 0;
          hpi.kill_timer_id = 0;

          Process.close_pid (pid);
          helper_state_changed (path, is_helper_enabled (path), false);
        });
        debug ("Spawned \"%s\" [%d]", path, child_pid);
      }
      catch (GLib.Error err)
      {
        warning ("%s", err.message);
        throw new DBus.Error.SPAWN_FAILED (err.message);
      }

      unowned HelperProcessInfo? hpi = update_helper (path);
      hpi.pid = (int) child_pid;

      helper_state_changed (path, true, child_pid != 0);
    }

    private unowned HelperProcessInfo? update_helper (string path)
    {
      unowned HelperProcessInfo? hpi = helper_process_info.lookup (path);
      if (hpi != null)
      {
        return hpi;
      }
      else
      {
        var pi = HelperProcessInfo ();
        pi.pid = 0;
        pi.kill_timer_id = 0;
        pi.dbus_appear_id = 0;
        pi.dbus_disappear_id = 0;
        helper_process_info.insert (path, pi);
        return helper_process_info.lookup (path);
      }
    }

    public void disable_helper (string path) throws DBus.Error
    {
      if (!is_helper_enabled (path)) return;
      // update our config list
      ValueArray enabled_helpers = new ValueArray (4);
      foreach (Value v in _helper_list)
      {
        if (v.get_string () != path) enabled_helpers.append (v);
      }
      this.helper_list = enabled_helpers;

      unowned HelperProcessInfo? hpi = update_helper (path);
      if (hpi.dbus_appear_id != 0)
      {
        SignalHandler.disconnect (watcher, hpi.dbus_appear_id);
        hpi.dbus_appear_id = 0;
      }
      if (hpi.dbus_disappear_id != 0)
      {
        SignalHandler.disconnect (watcher, hpi.dbus_disappear_id);
        hpi.dbus_disappear_id = 0;
      }

      if (hpi.pid == 0)
      {
        helper_state_changed (path, false, false);
        return;
      }

      kill_helper (path);

      helper_state_changed (path, false, get_helper_pid (path) != 0);
    }

    private void kill_helper (string path)
    {
      unowned HelperProcessInfo? hpi = update_helper (path);

      if (hpi.pid == 0) return;

      debug ("Sending SIGTERM to %d", hpi.pid);
      Posix.kill ((Posix.pid_t)hpi.pid, Posix.SIGTERM);

      if (hpi.kill_timer_id == 0)
      {
        hpi.kill_timer_id = Timeout.add (2000, () =>
        {
          if (hpi.pid != 0)
          {
            debug ("Sending SIGKILL to %d", hpi.pid);
            Posix.kill ((Posix.pid_t)hpi.pid, Posix.SIGKILL);
          }
          hpi.kill_timer_id = 0;
          return false;
        });
      }
    }

    private void kill_all ()
    {
      foreach (unowned string path in helper_process_info.get_keys ())
      {
        kill_helper (path);
      }
    }

    public async bool install_helper (string filename) throws DBus.Error
    {
      debug ("Trying to install %s", filename);
      Pid pid;
      string[] argv;

      // we'll use "tar -tf [filename]" to check if it contains /metadata/*.info
      try
      {
        int standard_output;
        bool metadata_file_found = false;
        string tar_command = "tar -t -f \"%s\"".printf (filename);
        Shell.parse_argv (tar_command, out argv);
        Process.spawn_async_with_pipes (null, argv, null,
                                        SpawnFlags.SEARCH_PATH |
                                        SpawnFlags.DO_NOT_REAP_CHILD,
                                        null,
                                        out pid,
                                        null,
                                        out standard_output,
                                        null);

        var re = new Regex ("^metadata/.*info$", RegexCompileFlags.OPTIMIZE);
        var chan = new IOChannel.unix_new (standard_output);
        var src_id = chan.add_watch (IOCondition.IN | IOCondition.HUP,
                                     (src, cond) =>
        {
          IOStatus io_status = IOStatus.NORMAL;
          while (io_status == IOStatus.NORMAL && !metadata_file_found)
          {
            string? line = null;
            io_status = src.read_line (out line, null, null);
            if (line != null) metadata_file_found = re.match (line, 0, null);
          }
          return true;
        });

        ChildWatch.add (pid, (p, status) =>
        {
          install_helper.callback ();
        });
        yield;

        Source.remove (src_id);

        if (!metadata_file_found)
        {
          warning ("Helper installation failed: %s", "No metadata file found!");
          return false;
        }
      }
      catch (GLib.Error err)
      {
        warning ("Helper installation failed: %s", err.message);
        return false;
      }

      // and now just "tar -C [user_data_dir] -x -f [filename]"
      try
      {
        string extract_command =
          "tar -C \"%s\" -x -f \"%s\"".printf (
            Environment.get_user_data_dir () + "/dockmanager",
            filename
          );

        Shell.parse_argv (extract_command, out argv);
        Process.spawn_async (null, argv, null,
                             SpawnFlags.SEARCH_PATH | 
                             SpawnFlags.DO_NOT_REAP_CHILD,
                             null,
                             out pid);

        int untar_status = 0;
        ChildWatch.add (pid, (p, status) =>
        {
          untar_status = status;
          install_helper.callback ();
        });
        yield;

        if (untar_status == 0)
        {
          return true;
        }
        else
        {
          warning ("Helper installation failed: tar returned errorcode %d!", untar_status);
        }
      }
      catch (GLib.Error err2)
      {
        warning ("Helper installation failed: %s", err2.message);
        return false;
      }

      return false;
    }

    public void show_preferences () throws DBus.Error
    {
      try
      {
        Process.spawn_command_line_async ("dockmanager-settings");
      }
      catch (GLib.SpawnError err)
      {
        warning ("%s", err.message);
        throw new DBus.Error.SPAWN_FAILED (err.message);
      }
    }

    public void embed_preferences (int64 xid,
                                   HashTable<string, Value?> hints)
      throws DBus.Error
    {
      string command = "dockmanager-settings -x %lld".printf (xid);

      unowned string key;
      unowned Value? val;
      HashTableIter<string,Value?> iter = HashTableIter<string,Value?> (hints);
      while (iter.next (out key, out val))
      {
        if (key == "no-install")
        {
          command = string.join (" ", command, "--no-install", null);
        }
      }

      try
      {
        Process.spawn_command_line_async (command);
      }
      catch (GLib.SpawnError err)
      {
        warning ("%s", err.message);
        throw new DBus.Error.SPAWN_FAILED (err.message);
      }
    }

    public HelperInfo[] get_all_helpers ()
    {
      int i = 0;

      HelperInfo[] helpers = new HelperInfo [all_scripts.length ()];
      foreach (unowned HelperInfo hi in all_scripts)
      {
        // our custom copy, dbus doesn't like NULLs
        helpers[i].path = hi.path;
        helpers[i].name = hi.name != null ? hi.name : "";
        helpers[i].description = hi.description != null ? hi.description : "";
        helpers[i].icon_name = hi.icon_name != null ? hi.icon_name : "";
        helpers[i].app_name = hi.app_name != null ? hi.app_name : "";
        helpers[i].app_available = hi.app_available;
        helpers[i].enabled = is_helper_enabled (hi.path);
        helpers[i].running = get_helper_pid (hi.path) != 0;
        helpers[i].dbus_name = hi.dbus_name != null ? hi.dbus_name : "";

        i++;
      }

      return helpers;
    }

    public void restart_all ()
    {
    }

    public static int main (string[] argv)
    {
      try
      {
        DesktopAgnostic.VFS.init ();

        var daemon = new HelperDaemon ();
        daemon.run ();

        DesktopAgnostic.VFS.shutdown ();
      }
      catch (GLib.Error err)
      {
        warning ("%s", err.message);
      }

      return 0;
    }
  }
}

