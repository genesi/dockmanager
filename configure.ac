AC_INIT([dockmanager], [0.1.1])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([.])
AC_CONFIG_HEADERS([config.h])

AM_INIT_AUTOMAKE([1.11 foreign tar-pax])
dnl -- Intl
IT_PROG_INTLTOOL([0.35.0])

dnl -- Populate top_srcdir variable
top_srcdir=$(readlink -f $0 | sed -e s/configure$//)

dnl Bzr Revno, if release set BZR_REVNO to the release version number
if test -d $top_srcdir/.bzr ; then
	BZR_REVNO=`bzr revno`
else
	BZR_REVNO=0.1
fi
AC_SUBST(BZR_REVNO)

if test -e $top_srcdir/.version_info ; then
   VERSION_INFO=`cat .version_info`
elif test -d $top_srcdir/.bzr ; then
   VERSION_INFO=`bzr version-info --custom \
   --template="bzr {branch_nick} r{revno}"`
else
   VERSION_INFO="Release"
fi
AC_SUBST(VERSION_INFO)

dnl pkg-config
AC_PATH_PROG(PKG_CONFIG, pkg-config, no)
if test "x$PKG_CONFIG" = "xno"; then
        AC_MSG_ERROR([You need to install pkg-config])
fi

AC_PROG_INSTALL
AC_PROG_CC
AC_STDC_HEADERS
AM_PROG_LIBTOOL

dnl ==============================================
dnl Check for vala
dnl ==============================================
AM_PROG_VALAC([0.10.0])

AM_SILENT_RULES([yes])

dnl ==============================================
dnl Check that we meet the dependencies
dnl ==============================================
MIN_GLIB_VERSION=2.18.0
MIN_GTK_VERSION=2.16.0
MIN_LDA_VERSION=0.3.9

LIBRARY_MODULES="glib-2.0 >= $MIN_GLIB_VERSION gobject-2.0 gio-2.0 desktop-agnostic >= $MIN_LDA_VERSION dbus-glib-1"

PKG_CHECK_MODULES(DOCKMANAGER_DAEMON, [$LIBRARY_MODULES])
PKG_CHECK_MODULES(GTK, [gtk+-2.0 >= $MIN_GTK_VERSION])

LDA_BINDIR="`$PKG_CONFIG --variable=exec_prefix desktop-agnostic`/bin"
AC_SUBST(LDA_BINDIR)

LDA_VAPIDIR="`$PKG_CONFIG --variable=vapidir desktop-agnostic`"
AC_SUBST(LDA_VAPIDIR)

dnl ==============================================
dnl GConf
dnl ==============================================
AM_GCONF_SOURCE_2
if test "$enable_schemas_install" != "no"; then
    AC_PATH_PROG(GCONFTOOL, gconftool-2, no)
    if test x"$GCONFTOOL" = xno; then
        AC_MSG_ERROR([gconftool-2 executable not found in your path - should be installed with GConf])
    fi
fi

dnl check for python
AM_PATH_PYTHON

dnl Expansions
AS_AC_EXPAND([PKGDATADIR], [$datadir/$PACKAGE_NAME])
AS_AC_EXPAND([DATADIR], [$datadir])
AS_AC_EXPAND([LIBDIR], [$libdir])
AS_AC_EXPAND([LIBEXECDIR], [$libexecdir])
AS_AC_EXPAND([SCHEMADIR], [$PKGDATADIR/schemas])

AC_DEFINE_UNQUOTED(PKGDATADIR, "$PKGDATADIR", [Package base directory])
AC_DEFINE_UNQUOTED(SCHEMAFILEDIR, "$SCHEMADIR", [Directory with config schema])

dnl {{{ enable debug release configuration
AC_ARG_ENABLE(debug,
	AC_HELP_STRING([--enable-debug],
		[Use 'DEBUG' Configuration [default=YES]]),
		enable_debug=yes, enable_debug=no)
AM_CONDITIONAL(ENABLE_DEBUG, test "x$enable_debug" = "xyes")
dnl }}}

AC_CONFIG_FILES([
Makefile
data/Makefile
metadata/Makefile
m4/Makefile
po/Makefile.in
daemon/Makefile
daemon/dockmanager.service
daemon/dockmanager-daemon.schema-ini
scripts/dockmanager/dockmanager.py
scripts/dockmanager/Makefile
scripts/Makefile
])

AC_OUTPUT

cat <<EOF

${PACKAGE}-${VERSION}

  Build Environment
    Install Prefix:     ${prefix}

  Build/Development
     Debug enabled:     ${enable_debug}

EOF
