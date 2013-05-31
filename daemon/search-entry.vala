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

using Gtk;

namespace DockManager
{
  public class SearchEntry: Entry
  {
    public bool delayed_clear { get; set; default = false; }
    public signal void search (string text);
    public signal void clear ();

    public int search_timeout { get; set; default = 500; }

    // FIXME: once we properly support gettext
    //private string default_text = _("Search...");
    private string default_text = "Search...";
    private uint search_timeout_id;
    private string current_search_text = "";

    public SearchEntry ()
    {
    }

    construct
    {
      this.set_text (default_text);
      this.changed.connect (this.queue_search);
      this.focus_in_event.connect (this.focus_in);
      this.focus_out_event.connect (this.focus_out);
      this.realize.connect_after (this.realized);

      this.icon_press.connect (this.icon_pressed);

      this.set_icon_from_stock (EntryIconPosition.PRIMARY, STOCK_FIND);
      this.set_icon_from_stock (EntryIconPosition.SECONDARY, STOCK_CLEAR);
    }

    private bool focus_in ()
    {
      if (base.get_text () == default_text)
      {
        this.modify_text (StateType.NORMAL, null);
        this.set_text ("");
      }

      return false;
    }

    private bool focus_out ()
    {
      if (base.get_text () == "")
      {
        this.modify_text (StateType.NORMAL,
                          this.get_style ().text[StateType.INSENSITIVE]);
        this.set_text (this.default_text);
      }

      return false;
    }

    private void realized ()
    {
      if (!has_focus)
      {
        this.modify_text (StateType.NORMAL,
                          this.get_style ().text[StateType.INSENSITIVE]);
      }
    }

    private void icon_pressed (EntryIconPosition pos, Gdk.Event event)
    {
      if (pos == EntryIconPosition.SECONDARY &&
        this.get_text () != default_text)
      {
        this.set_text ("");
        if (!has_focus) this.focus_out ();
      }
    }

    private void queue_search ()
    {
      if (this.search_timeout_id != 0)
      {
        GLib.Source.remove (this.search_timeout_id);
        this.search_timeout_id = 0;
      }

      unowned string t = base.get_text ();
      if ((t == default_text || t == "") && !delayed_clear)
      {
        if (current_search_text != "")
        {
          current_search_text = "";
          clear ();
        }
      }
      else
      {
        this.search_timeout_id = Timeout.add (search_timeout,
                                              this.typing_timeout);
      }
    }

    private bool typing_timeout ()
    {
      unowned string term = base.get_text ();
      if (term != default_text && term != "")
      {
        current_search_text = term;
        search (term);
      }
      else if (delayed_clear)
      {
        current_search_text = "";
        clear ();
      }

      this.search_timeout_id = 0;

      return false;
    }

    public new unowned string? get_text ()
    {
      return current_search_text;
    }
  }
}
