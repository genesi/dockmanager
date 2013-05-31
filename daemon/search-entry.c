/* search-entry.c generated by valac 0.12.1, the Vala compiler
 * generated from search-entry.vala, do not modify */

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

#include <glib.h>
#include <glib-object.h>
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include <gdk/gdk.h>


#define DOCK_MANAGER_TYPE_SEARCH_ENTRY (dock_manager_search_entry_get_type ())
#define DOCK_MANAGER_SEARCH_ENTRY(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), DOCK_MANAGER_TYPE_SEARCH_ENTRY, DockManagerSearchEntry))
#define DOCK_MANAGER_SEARCH_ENTRY_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST ((klass), DOCK_MANAGER_TYPE_SEARCH_ENTRY, DockManagerSearchEntryClass))
#define DOCK_MANAGER_IS_SEARCH_ENTRY(obj) (G_TYPE_CHECK_INSTANCE_TYPE ((obj), DOCK_MANAGER_TYPE_SEARCH_ENTRY))
#define DOCK_MANAGER_IS_SEARCH_ENTRY_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass), DOCK_MANAGER_TYPE_SEARCH_ENTRY))
#define DOCK_MANAGER_SEARCH_ENTRY_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS ((obj), DOCK_MANAGER_TYPE_SEARCH_ENTRY, DockManagerSearchEntryClass))

typedef struct _DockManagerSearchEntry DockManagerSearchEntry;
typedef struct _DockManagerSearchEntryClass DockManagerSearchEntryClass;
typedef struct _DockManagerSearchEntryPrivate DockManagerSearchEntryPrivate;
#define _g_free0(var) (var = (g_free (var), NULL))

struct _DockManagerSearchEntry {
	GtkEntry parent_instance;
	DockManagerSearchEntryPrivate * priv;
};

struct _DockManagerSearchEntryClass {
	GtkEntryClass parent_class;
};

struct _DockManagerSearchEntryPrivate {
	gboolean _delayed_clear;
	gint _search_timeout;
	gchar* default_text;
	guint search_timeout_id;
	gchar* current_search_text;
};


static gpointer dock_manager_search_entry_parent_class = NULL;

GType dock_manager_search_entry_get_type (void) G_GNUC_CONST;
#define DOCK_MANAGER_SEARCH_ENTRY_GET_PRIVATE(o) (G_TYPE_INSTANCE_GET_PRIVATE ((o), DOCK_MANAGER_TYPE_SEARCH_ENTRY, DockManagerSearchEntryPrivate))
enum  {
	DOCK_MANAGER_SEARCH_ENTRY_DUMMY_PROPERTY,
	DOCK_MANAGER_SEARCH_ENTRY_DELAYED_CLEAR,
	DOCK_MANAGER_SEARCH_ENTRY_SEARCH_TIMEOUT
};
DockManagerSearchEntry* dock_manager_search_entry_new (void);
DockManagerSearchEntry* dock_manager_search_entry_construct (GType object_type);
static gboolean dock_manager_search_entry_focus_in (DockManagerSearchEntry* self);
static gboolean dock_manager_search_entry_focus_out (DockManagerSearchEntry* self);
static void dock_manager_search_entry_realized (DockManagerSearchEntry* self);
static void dock_manager_search_entry_icon_pressed (DockManagerSearchEntry* self, GtkEntryIconPosition pos, GdkEvent* event);
const gchar* dock_manager_search_entry_get_text (DockManagerSearchEntry* self);
static void dock_manager_search_entry_queue_search (DockManagerSearchEntry* self);
gboolean dock_manager_search_entry_get_delayed_clear (DockManagerSearchEntry* self);
gint dock_manager_search_entry_get_search_timeout (DockManagerSearchEntry* self);
static gboolean dock_manager_search_entry_typing_timeout (DockManagerSearchEntry* self);
static gboolean _dock_manager_search_entry_typing_timeout_gsource_func (gpointer self);
void dock_manager_search_entry_set_delayed_clear (DockManagerSearchEntry* self, gboolean value);
void dock_manager_search_entry_set_search_timeout (DockManagerSearchEntry* self, gint value);
static GObject * dock_manager_search_entry_constructor (GType type, guint n_construct_properties, GObjectConstructParam * construct_properties);
static void _dock_manager_search_entry_queue_search_gtk_editable_changed (GtkEditable* _sender, gpointer self);
static gboolean _dock_manager_search_entry_focus_in_gtk_widget_focus_in_event (GtkWidget* _sender, GdkEventFocus* event, gpointer self);
static gboolean _dock_manager_search_entry_focus_out_gtk_widget_focus_out_event (GtkWidget* _sender, GdkEventFocus* event, gpointer self);
static void _dock_manager_search_entry_realized_gtk_widget_realize (GtkWidget* _sender, gpointer self);
static void _dock_manager_search_entry_icon_pressed_gtk_entry_icon_press (GtkEntry* _sender, GtkEntryIconPosition p0, GdkEvent* p1, gpointer self);
static void dock_manager_search_entry_finalize (GObject* obj);
static void _vala_dock_manager_search_entry_get_property (GObject * object, guint property_id, GValue * value, GParamSpec * pspec);
static void _vala_dock_manager_search_entry_set_property (GObject * object, guint property_id, const GValue * value, GParamSpec * pspec);


DockManagerSearchEntry* dock_manager_search_entry_construct (GType object_type) {
	DockManagerSearchEntry * self = NULL;
	self = (DockManagerSearchEntry*) g_object_new (object_type, NULL);
	return self;
}


DockManagerSearchEntry* dock_manager_search_entry_new (void) {
	return dock_manager_search_entry_construct (DOCK_MANAGER_TYPE_SEARCH_ENTRY);
}


static gboolean dock_manager_search_entry_focus_in (DockManagerSearchEntry* self) {
	gboolean result = FALSE;
	const gchar* _tmp0_ = NULL;
	g_return_val_if_fail (self != NULL, FALSE);
	_tmp0_ = gtk_entry_get_text (GTK_ENTRY (self));
	if (g_strcmp0 (_tmp0_, self->priv->default_text) == 0) {
		gtk_widget_modify_text ((GtkWidget*) self, GTK_STATE_NORMAL, NULL);
		gtk_entry_set_text ((GtkEntry*) self, "");
	}
	result = FALSE;
	return result;
}


static gboolean dock_manager_search_entry_focus_out (DockManagerSearchEntry* self) {
	gboolean result = FALSE;
	const gchar* _tmp0_ = NULL;
	g_return_val_if_fail (self != NULL, FALSE);
	_tmp0_ = gtk_entry_get_text (GTK_ENTRY (self));
	if (g_strcmp0 (_tmp0_, "") == 0) {
		GtkStyle* _tmp1_ = NULL;
		GdkColor _tmp2_;
		_tmp1_ = gtk_widget_get_style ((GtkWidget*) self);
		_tmp2_ = _tmp1_->text[GTK_STATE_INSENSITIVE];
		gtk_widget_modify_text ((GtkWidget*) self, GTK_STATE_NORMAL, &_tmp2_);
		gtk_entry_set_text ((GtkEntry*) self, self->priv->default_text);
	}
	result = FALSE;
	return result;
}


static void dock_manager_search_entry_realized (DockManagerSearchEntry* self) {
	gboolean _tmp0_;
	g_return_if_fail (self != NULL);
	g_object_get ((GtkWidget*) self, "has-focus", &_tmp0_, NULL);
	if (!_tmp0_) {
		GtkStyle* _tmp1_ = NULL;
		GdkColor _tmp2_;
		_tmp1_ = gtk_widget_get_style ((GtkWidget*) self);
		_tmp2_ = _tmp1_->text[GTK_STATE_INSENSITIVE];
		gtk_widget_modify_text ((GtkWidget*) self, GTK_STATE_NORMAL, &_tmp2_);
	}
}


static void dock_manager_search_entry_icon_pressed (DockManagerSearchEntry* self, GtkEntryIconPosition pos, GdkEvent* event) {
	gboolean _tmp0_ = FALSE;
	g_return_if_fail (self != NULL);
	g_return_if_fail (event != NULL);
	if (pos == GTK_ENTRY_ICON_SECONDARY) {
		const gchar* _tmp1_ = NULL;
		_tmp1_ = dock_manager_search_entry_get_text (self);
		_tmp0_ = g_strcmp0 (_tmp1_, self->priv->default_text) != 0;
	} else {
		_tmp0_ = FALSE;
	}
	if (_tmp0_) {
		gboolean _tmp2_;
		gtk_entry_set_text ((GtkEntry*) self, "");
		g_object_get ((GtkWidget*) self, "has-focus", &_tmp2_, NULL);
		if (!_tmp2_) {
			dock_manager_search_entry_focus_out (self);
		}
	}
}


static gboolean _dock_manager_search_entry_typing_timeout_gsource_func (gpointer self) {
	gboolean result;
	result = dock_manager_search_entry_typing_timeout (self);
	return result;
}


static void dock_manager_search_entry_queue_search (DockManagerSearchEntry* self) {
	const gchar* _tmp0_ = NULL;
	const gchar* t;
	gboolean _tmp1_ = FALSE;
	gboolean _tmp2_ = FALSE;
	g_return_if_fail (self != NULL);
	if (self->priv->search_timeout_id != 0) {
		g_source_remove (self->priv->search_timeout_id);
		self->priv->search_timeout_id = (guint) 0;
	}
	_tmp0_ = gtk_entry_get_text (GTK_ENTRY (self));
	t = _tmp0_;
	if (g_strcmp0 (t, self->priv->default_text) == 0) {
		_tmp2_ = TRUE;
	} else {
		_tmp2_ = g_strcmp0 (t, "") == 0;
	}
	if (_tmp2_) {
		_tmp1_ = !self->priv->_delayed_clear;
	} else {
		_tmp1_ = FALSE;
	}
	if (_tmp1_) {
		if (g_strcmp0 (self->priv->current_search_text, "") != 0) {
			gchar* _tmp3_;
			_tmp3_ = g_strdup ("");
			_g_free0 (self->priv->current_search_text);
			self->priv->current_search_text = _tmp3_;
			g_signal_emit_by_name (self, "clear");
		}
	} else {
		guint _tmp4_;
		_tmp4_ = g_timeout_add_full (G_PRIORITY_DEFAULT, (guint) self->priv->_search_timeout, _dock_manager_search_entry_typing_timeout_gsource_func, g_object_ref (self), g_object_unref);
		self->priv->search_timeout_id = _tmp4_;
	}
}


static gboolean dock_manager_search_entry_typing_timeout (DockManagerSearchEntry* self) {
	gboolean result = FALSE;
	const gchar* _tmp0_ = NULL;
	const gchar* term;
	gboolean _tmp1_ = FALSE;
	g_return_val_if_fail (self != NULL, FALSE);
	_tmp0_ = gtk_entry_get_text (GTK_ENTRY (self));
	term = _tmp0_;
	if (g_strcmp0 (term, self->priv->default_text) != 0) {
		_tmp1_ = g_strcmp0 (term, "") != 0;
	} else {
		_tmp1_ = FALSE;
	}
	if (_tmp1_) {
		gchar* _tmp2_;
		_tmp2_ = g_strdup (term);
		_g_free0 (self->priv->current_search_text);
		self->priv->current_search_text = _tmp2_;
		g_signal_emit_by_name (self, "search", term);
	} else {
		if (self->priv->_delayed_clear) {
			gchar* _tmp3_;
			_tmp3_ = g_strdup ("");
			_g_free0 (self->priv->current_search_text);
			self->priv->current_search_text = _tmp3_;
			g_signal_emit_by_name (self, "clear");
		}
	}
	self->priv->search_timeout_id = (guint) 0;
	result = FALSE;
	return result;
}


const gchar* dock_manager_search_entry_get_text (DockManagerSearchEntry* self) {
	const gchar* result = NULL;
	g_return_val_if_fail (self != NULL, NULL);
	result = self->priv->current_search_text;
	return result;
}


gboolean dock_manager_search_entry_get_delayed_clear (DockManagerSearchEntry* self) {
	gboolean result;
	g_return_val_if_fail (self != NULL, FALSE);
	result = self->priv->_delayed_clear;
	return result;
}


void dock_manager_search_entry_set_delayed_clear (DockManagerSearchEntry* self, gboolean value) {
	g_return_if_fail (self != NULL);
	self->priv->_delayed_clear = value;
	g_object_notify ((GObject *) self, "delayed-clear");
}


gint dock_manager_search_entry_get_search_timeout (DockManagerSearchEntry* self) {
	gint result;
	g_return_val_if_fail (self != NULL, 0);
	result = self->priv->_search_timeout;
	return result;
}


void dock_manager_search_entry_set_search_timeout (DockManagerSearchEntry* self, gint value) {
	g_return_if_fail (self != NULL);
	self->priv->_search_timeout = value;
	g_object_notify ((GObject *) self, "search-timeout");
}


static void _dock_manager_search_entry_queue_search_gtk_editable_changed (GtkEditable* _sender, gpointer self) {
	dock_manager_search_entry_queue_search (self);
}


static gboolean _dock_manager_search_entry_focus_in_gtk_widget_focus_in_event (GtkWidget* _sender, GdkEventFocus* event, gpointer self) {
	gboolean result;
	result = dock_manager_search_entry_focus_in (self);
	return result;
}


static gboolean _dock_manager_search_entry_focus_out_gtk_widget_focus_out_event (GtkWidget* _sender, GdkEventFocus* event, gpointer self) {
	gboolean result;
	result = dock_manager_search_entry_focus_out (self);
	return result;
}


static void _dock_manager_search_entry_realized_gtk_widget_realize (GtkWidget* _sender, gpointer self) {
	dock_manager_search_entry_realized (self);
}


static void _dock_manager_search_entry_icon_pressed_gtk_entry_icon_press (GtkEntry* _sender, GtkEntryIconPosition p0, GdkEvent* p1, gpointer self) {
	dock_manager_search_entry_icon_pressed (self, p0, p1);
}


static GObject * dock_manager_search_entry_constructor (GType type, guint n_construct_properties, GObjectConstructParam * construct_properties) {
	GObject * obj;
	GObjectClass * parent_class;
	DockManagerSearchEntry * self;
	parent_class = G_OBJECT_CLASS (dock_manager_search_entry_parent_class);
	obj = parent_class->constructor (type, n_construct_properties, construct_properties);
	self = DOCK_MANAGER_SEARCH_ENTRY (obj);
	gtk_entry_set_text ((GtkEntry*) self, self->priv->default_text);
	g_signal_connect_object ((GtkEditable*) self, "changed", (GCallback) _dock_manager_search_entry_queue_search_gtk_editable_changed, self, 0);
	g_signal_connect_object ((GtkWidget*) self, "focus-in-event", (GCallback) _dock_manager_search_entry_focus_in_gtk_widget_focus_in_event, self, 0);
	g_signal_connect_object ((GtkWidget*) self, "focus-out-event", (GCallback) _dock_manager_search_entry_focus_out_gtk_widget_focus_out_event, self, 0);
	g_signal_connect_object ((GtkWidget*) self, "realize", (GCallback) _dock_manager_search_entry_realized_gtk_widget_realize, self, G_CONNECT_AFTER);
	g_signal_connect_object ((GtkEntry*) self, "icon-press", (GCallback) _dock_manager_search_entry_icon_pressed_gtk_entry_icon_press, self, 0);
	gtk_entry_set_icon_from_stock ((GtkEntry*) self, GTK_ENTRY_ICON_PRIMARY, GTK_STOCK_FIND);
	gtk_entry_set_icon_from_stock ((GtkEntry*) self, GTK_ENTRY_ICON_SECONDARY, GTK_STOCK_CLEAR);
	return obj;
}


static void dock_manager_search_entry_class_init (DockManagerSearchEntryClass * klass) {
	dock_manager_search_entry_parent_class = g_type_class_peek_parent (klass);
	g_type_class_add_private (klass, sizeof (DockManagerSearchEntryPrivate));
	G_OBJECT_CLASS (klass)->get_property = _vala_dock_manager_search_entry_get_property;
	G_OBJECT_CLASS (klass)->set_property = _vala_dock_manager_search_entry_set_property;
	G_OBJECT_CLASS (klass)->constructor = dock_manager_search_entry_constructor;
	G_OBJECT_CLASS (klass)->finalize = dock_manager_search_entry_finalize;
	g_object_class_install_property (G_OBJECT_CLASS (klass), DOCK_MANAGER_SEARCH_ENTRY_DELAYED_CLEAR, g_param_spec_boolean ("delayed-clear", "delayed-clear", "delayed-clear", FALSE, G_PARAM_STATIC_NAME | G_PARAM_STATIC_NICK | G_PARAM_STATIC_BLURB | G_PARAM_READABLE | G_PARAM_WRITABLE));
	g_object_class_install_property (G_OBJECT_CLASS (klass), DOCK_MANAGER_SEARCH_ENTRY_SEARCH_TIMEOUT, g_param_spec_int ("search-timeout", "search-timeout", "search-timeout", G_MININT, G_MAXINT, 500, G_PARAM_STATIC_NAME | G_PARAM_STATIC_NICK | G_PARAM_STATIC_BLURB | G_PARAM_READABLE | G_PARAM_WRITABLE));
	g_signal_new ("search", DOCK_MANAGER_TYPE_SEARCH_ENTRY, G_SIGNAL_RUN_LAST, 0, NULL, NULL, g_cclosure_marshal_VOID__STRING, G_TYPE_NONE, 1, G_TYPE_STRING);
	g_signal_new ("clear", DOCK_MANAGER_TYPE_SEARCH_ENTRY, G_SIGNAL_RUN_LAST, 0, NULL, NULL, g_cclosure_marshal_VOID__VOID, G_TYPE_NONE, 0);
}


static void dock_manager_search_entry_instance_init (DockManagerSearchEntry * self) {
	gchar* _tmp0_;
	gchar* _tmp1_;
	self->priv = DOCK_MANAGER_SEARCH_ENTRY_GET_PRIVATE (self);
	self->priv->_delayed_clear = FALSE;
	self->priv->_search_timeout = 500;
	_tmp0_ = g_strdup ("Search...");
	self->priv->default_text = _tmp0_;
	_tmp1_ = g_strdup ("");
	self->priv->current_search_text = _tmp1_;
}


static void dock_manager_search_entry_finalize (GObject* obj) {
	DockManagerSearchEntry * self;
	self = DOCK_MANAGER_SEARCH_ENTRY (obj);
	_g_free0 (self->priv->default_text);
	_g_free0 (self->priv->current_search_text);
	G_OBJECT_CLASS (dock_manager_search_entry_parent_class)->finalize (obj);
}


GType dock_manager_search_entry_get_type (void) {
	static volatile gsize dock_manager_search_entry_type_id__volatile = 0;
	if (g_once_init_enter (&dock_manager_search_entry_type_id__volatile)) {
		static const GTypeInfo g_define_type_info = { sizeof (DockManagerSearchEntryClass), (GBaseInitFunc) NULL, (GBaseFinalizeFunc) NULL, (GClassInitFunc) dock_manager_search_entry_class_init, (GClassFinalizeFunc) NULL, NULL, sizeof (DockManagerSearchEntry), 0, (GInstanceInitFunc) dock_manager_search_entry_instance_init, NULL };
		GType dock_manager_search_entry_type_id;
		dock_manager_search_entry_type_id = g_type_register_static (GTK_TYPE_ENTRY, "DockManagerSearchEntry", &g_define_type_info, 0);
		g_once_init_leave (&dock_manager_search_entry_type_id__volatile, dock_manager_search_entry_type_id);
	}
	return dock_manager_search_entry_type_id__volatile;
}


static void _vala_dock_manager_search_entry_get_property (GObject * object, guint property_id, GValue * value, GParamSpec * pspec) {
	DockManagerSearchEntry * self;
	self = DOCK_MANAGER_SEARCH_ENTRY (object);
	switch (property_id) {
		case DOCK_MANAGER_SEARCH_ENTRY_DELAYED_CLEAR:
		g_value_set_boolean (value, dock_manager_search_entry_get_delayed_clear (self));
		break;
		case DOCK_MANAGER_SEARCH_ENTRY_SEARCH_TIMEOUT:
		g_value_set_int (value, dock_manager_search_entry_get_search_timeout (self));
		break;
		default:
		G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
		break;
	}
}


static void _vala_dock_manager_search_entry_set_property (GObject * object, guint property_id, const GValue * value, GParamSpec * pspec) {
	DockManagerSearchEntry * self;
	self = DOCK_MANAGER_SEARCH_ENTRY (object);
	switch (property_id) {
		case DOCK_MANAGER_SEARCH_ENTRY_DELAYED_CLEAR:
		dock_manager_search_entry_set_delayed_clear (self, g_value_get_boolean (value));
		break;
		case DOCK_MANAGER_SEARCH_ENTRY_SEARCH_TIMEOUT:
		dock_manager_search_entry_set_search_timeout (self, g_value_get_int (value));
		break;
		default:
		G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
		break;
	}
}



