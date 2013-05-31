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

using DesktopAgnostic;

namespace DockManager
{
  private static int64 EMBED_XID = 0;
  private static bool NO_INSTALL = false;

  const OptionEntry[] options =
  {
    {
      "embed-xid", 'x', 0, OptionArg.INT64,
      out EMBED_XID, "Window XID where the GUI will be embedded.", ""
    },
    {
      "no-install", 'i', 0, OptionArg.NONE,
      out NO_INSTALL, "Don't display the install button.", ""
    },
    {
      null
    }
  };

  class HelperTileObject: AbstractTileObject
  {
    private Gtk.Button help_button;
    private Gtk.Button uninstall_button;

    public string helper_path { get; construct; }

    public HelperTileObject (HelperInfo hi)
    {
      GLib.Object (name: hi.name,
                   description: hi.description,
                   icon: hi.icon_name,
                   helper_path: hi.path);
    }

    construct
    {
      // hmm weird, why there's no AddButtonStock? = Gtk.STOCK_EXECUTE;
      sub_description_title = "Status"; // FIXME: i18n

      if (helper_path.has_prefix (Environment.get_home_dir ()))
      {
        uninstall_button = new Gtk.Button.with_label ("Uninstall"); // FIXME: i18n
        add_user_button (uninstall_button);
      }

      help_button = new Gtk.Button ();
      help_button.set_image (
          new Gtk.Image.from_stock (Gtk.STOCK_HELP,
                                    Gtk.IconSize.SMALL_TOOLBAR));
      help_button.set_tooltip_markup ("About this helper"); // FIXME: i18n
      help_button.clicked.connect (() =>
      {
        string id = Path.get_basename (helper_path).split (".")[0];
        string address = "http://wiki.go-docky.com/index.php?title=%s_Helper". printf (id);
        Process.spawn_command_line_async ("xdg-open %s".printf (address));
      });
      add_user_button (help_button);

      add_button_tooltip = "Enable this helper"; // FIXME: i18n
      remove_button_tooltip = "Disable this helper"; // FIXME: i18n
    }

    public void update_state (bool enabled, bool running)
    {
      this.enabled = enabled;

      if (!enabled)
      {
        sub_description_text = "Disabled"; // i18n!
      }
      else
      {
        sub_description_text = running ? "Running" : "Enabled"; // i18n!
      }
    }
  }

  class PreferencesBin : Gtk.VBox
  {
    private Gtk.ScrolledWindow scroll;
    private Gtk.ComboBox combobox;
    private SearchEntry search_entry;
    private TileView tile_view;

    private List<HelperInfo?> all_helpers;
    private DaemonInterface dbus_interface;

    PreferencesBin ()
    {
      GLib.Object (spacing: 6);
    }

    enum HelperFilterType
    {
      USABLE = 0,
      ENABLED,
      DISABLED,
      ALL,

      N_TYPES
    }

    construct
    {
      all_helpers = new List<HelperInfo?> ();
      var hbox = new Gtk.HBox (false, 6);

      combobox = new Gtk.ComboBox.text ();
      // FIXME: i18n!
      combobox.append_text ("Usable");
      combobox.append_text ("Enabled");
      combobox.append_text ("Disabled");
      combobox.append_text ("All");
      combobox.set_active (0);
      combobox.changed.connect (this.update_helpers);
      hbox.pack_start (combobox, false);
      this.pack_start (hbox, false);

      search_entry = new SearchEntry ();
      search_entry.search_timeout = 100;
      search_entry.search.connect (() => { update_helpers (); });
      search_entry.clear.connect (() => { update_helpers (); });
      hbox.pack_start (search_entry);

      if (NO_INSTALL == false)
      {
        var button = new Gtk.Button.with_label ("Install");
        button.set_sensitive (false);
        hbox.pack_start (button, false);
      }

      hbox.show_all ();

      scroll = new Gtk.ScrolledWindow (null, null);
      scroll.set_policy (Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC);
      tile_view = new TileView ();
      tile_view.show ();
      scroll.add_with_viewport (tile_view);
      scroll.show ();
      this.pack_start (scroll);

      this.run ();
    }

    public void run ()
    {
      try
      {
        var connection = DBus.Bus.get (DBus.BusType.SESSION);
        dbus_interface = (DaemonInterface)
          connection.get_object (DBUS_UNIQUE_NAME,
                                 DBUS_OBJECT_PATH_NAME,
                                 DBUS_INTERFACE_NAME);

        dbus_interface.helper_state_changed.connect (this.helper_changed);
        HelperInfo[] helpers = dbus_interface.get_all_helpers ();
        foreach (unowned HelperInfo? helper in helpers)
        {
          all_helpers.append (helper);
        }
        all_helpers.sort ((a, b) =>
        {
          unowned HelperInfo? hi1 = (HelperInfo?) a;
          unowned HelperInfo? hi2 = (HelperInfo?) b;
          return strcmp (hi1.name, hi2.name);
        });

        update_helpers ();
      }
      catch (DBus.Error err)
      {
        warning ("%s", err.message);
      }
    }

    private void update_helpers ()
    {
      tile_view.clear ();
      HelperFilterType filter = (HelperFilterType) combobox.get_active ();
      string search_filter = search_entry.get_text ();

      foreach (unowned HelperInfo? helper in all_helpers)
      {
        if (filter == HelperFilterType.USABLE && !helper.app_available)
        {
          continue;
        }

        if (filter == HelperFilterType.ENABLED && !helper.enabled)
        {
          continue;
        }

        if (filter == HelperFilterType.DISABLED && helper.enabled)
        {
          continue;
        }

        if (search_filter != null && search_filter != "")
        {
          Regex r = new Regex (search_filter, RegexCompileFlags.CASELESS);
          if (!r.match (helper.description) && !r.match (helper.name))
          {
            continue;
          }
        }

        var h_tile = new HelperTileObject (helper);
        h_tile.update_state (helper.enabled, helper.running);
        tile_view.append_tile (h_tile);

        h_tile.active_changed.connect ((tile_obj) =>
        {
          var helper_tile_obj = tile_obj as HelperTileObject;
          if (!helper_tile_obj.enabled)
          {
            dbus_interface.enable_helper (helper_tile_obj.helper_path);
          }
          else
          {
            dbus_interface.disable_helper (helper_tile_obj.helper_path);
          }
        });
      }
    }

    private void helper_changed (string path, bool enabled, bool running)
    {
      debug ("%s is now %s, [%s]",
             Path.get_basename (path),
             enabled ? "enabled" : "disabled",
             running ? "running" : "stopped");

      // update internal list
      foreach (unowned HelperInfo? helper in all_helpers)
      {
        if (helper.path == path)
        {
          helper.enabled = enabled;
          helper.running = running;
        }
      }

      // update TileView
      List<unowned AbstractTileObject> tiles = tile_view.get_tiles ();

      foreach (unowned AbstractTileObject to in tiles)
      {
        var helper_tile = to as HelperTileObject;
        if (path == helper_tile.helper_path)
        {
          helper_tile.update_state (enabled, running);
          break;
        }
      }
    }

    public static int main (string[] argv)
    {
      var context = new OptionContext (" - Dockmanager-settings Options");
      context.add_main_entries (options, null);
      context.add_group (Gtk.get_option_group (false));
      context.parse (ref argv);

      Gtk.init (ref argv); // necessary?
      try
      {
        DesktopAgnostic.VFS.init ();

        PreferencesBin prefs_bin = new PreferencesBin ();
        prefs_bin.show ();

        if (EMBED_XID == 0)
        {
          var window = new Gtk.Window ();
          window.set_title ("Dockmanager preferences");
          window.add (prefs_bin);
          window.set_default_size (400, 450);
          window.border_width = 12;
          window.destroy.connect (Gtk.main_quit);
          window.show ();
        }
        else
        {
          var plug = new Gtk.Plug ((Gdk.NativeWindow) 0);
          plug.delete_event.connect (() =>
          {
            Gtk.main_quit ();
            return false;
          });
          plug.add (prefs_bin);
          plug.@construct ((Gdk.NativeWindow) EMBED_XID);
          plug.show ();
          // the plug gets unreffed, yet it still lives... hmm?!
        }

        Gtk.main ();

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

