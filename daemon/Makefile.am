include $(top_srcdir)/Makefile.schemas

# config-related
schema_in_files = dockmanager-daemon.schema-ini.in

# global
install-data-local: install-gconf-schemas

VALAFLAGS = \
	--enable-experimental \
	--pkg dbus-glib-1 \
	--vapidir=$(LDA_VAPIDIR) \
	--pkg desktop-agnostic-cfg \
	--pkg gtk+-2.0 \
	build.vapi \
	signal-fix.vapi \
	$(NULL)

dockmanager_daemondir = $(libexecdir)
dockmanager_guidir = $(bindir)

dockmanager_daemon_PROGRAMS = \
	dockmanager-daemon \
	$(NULL)

dockmanager_gui_PROGRAMS = \
	dockmanager-settings \
	$(NULL)

dockmanager_daemon_CFLAGS = $(DOCKMANAGER_DAEMON_CFLAGS)
dockmanager_daemon_LDADD = $(DOCKMANAGER_DAEMON_LIBS)
dockmanager_daemon_SOURCES = \
	dockmanager-common.vala \
	dockmanager-daemon.vala \
	dbus-helper.vala \
	$(NULL)

dockmanager_settings_CFLAGS = $(DOCKMANAGER_DAEMON_CFLAGS) $(GTK_CFLAGS)
dockmanager_settings_LDADD = $(DOCKMANAGER_DAEMON_LIBS) $(GTK_LIBS)
dockmanager_settings_SOURCES = \
	dockmanager-common.vala \
	dockmanager-settings.vala \
	search-entry.vala \
	abstract-tile-object.vala \
	tile.vala \
	tile-view.vala \
	wrap-label.vala \
	$(NULL)

# service file
servicedir = $(datarootdir)/dbus-1/services
service_DATA = dockmanager.service

EXTRA_DIST = dockmanager.service.in

CLEANFILES = \
	dockmanager.service \
	$(schemas_DATA) \
	$(schema_in_DATA) \
	$(schema_DATA) \
	$(NULL)
