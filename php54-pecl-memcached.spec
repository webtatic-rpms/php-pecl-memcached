# spec file for php-pecl-memcached
#
# Copyright (c) 2009-2014 Remi Collet
# License: CC-BY-SA
# http://creativecommons.org/licenses/by-sa/3.0/
#
# Please, preserve the changelog entries
#

%{!?__pecl:      %global __pecl       %{_bindir}/pecl}

%global basepkg     php54w
%global with_zts    0%{?__ztsphp:1}
%global with_tests  %{?_with_tests:1}%{!?_with_tests:0}
%global pecl_name   memcached

Summary:      Extension to work with the Memcached caching daemon
Name:         %{basepkg}-pecl-memcached
Version:      2.2.0
Release:      2%{?dist}
# memcached is PHP, FastLZ is MIT
License:      PHP and MIT
Group:        Development/Languages
URL:          http://pecl.php.net/package/%{pecl_name}

Source0:      http://pecl.php.net/get/%{pecl_name}-%{version}.tgz

BuildRoot:    %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: %{basepkg}-devel >= 5.2.10
BuildRequires: %{basepkg}-pear
BuildRequires: %{basepkg}-pecl-igbinary-devel
BuildRequires: libevent-devel
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
BuildRequires: libmemcached-devel > 1
%else
BuildRequires: libmemcached10-devel > 1
%endif
BuildRequires: zlib-devel
BuildRequires: cyrus-sasl-devel
%if %{with_tests}
BuildRequires: memcached
%endif

Requires(post): %{__pecl}
Requires(postun): %{__pecl}

Requires:     php-pecl-igbinary%{?_isa}
Requires:     php(zend-abi) = %{php_zend_api}
Requires:     php(api) = %{php_core_api}

Provides:     php-%{pecl_name} = %{version}
Provides:     php-%{pecl_name}%{?_isa} = %{version}
Provides:     php-pecl(%{pecl_name}) = %{version}
Provides:     php-pecl(%{pecl_name})%{?_isa} = %{version}
Provides:     php-pecl-%{pecl_name} = %{version}
Provides:     php-pecl-%{pecl_name}%{?_isa} = %{version}

%if 0%{?fedora} < 20 && 0%{?rhel} < 7
# Filter private shared
%{?filter_provides_in: %filter_provides_in %{_libdir}/.*\.so$}
%{?filter_setup}
%endif


%description
This extension uses libmemcached library to provide API for communicating
with memcached servers.

memcached is a high-performance, distributed memory object caching system,
generic in nature, but intended for use in speeding up dynamic web 
applications by alleviating database load.

It also provides a session handler (memcached). 


%prep 
%setup -c -q

mv %{pecl_name}-%{version}%{?prever} NTS

# Chech version as upstream often forget to update this
extver=$(sed -n '/#define PHP_MEMCACHED_VERSION/{s/.* "//;s/".*$//;p}' NTS/php_memcached.h)
if test "x${extver}" != "x%{version}"; then
   : Error: Upstream HTTP version is now ${extver}, expecting %{version}.
   : Update the pdover macro and rebuild.
   exit 1
fi

cat > %{pecl_name}.ini << 'EOF'
; Enable %{pecl_name} extension module
extension=%{pecl_name}.so

; ----- Options to use the memcached session handler

; RPM note : save_handler and save_path are defined
; for mod_php, in /etc/httpd/conf.d/php.conf
; for php-fpm, in /etc/php-fpm.d/*conf

;  Use memcache as a session handler
;session.save_handler=memcached
;  Defines a comma separated list of server urls to use for session storage
;session.save_path="localhost:11211"

; ----- Configuration options
; http://php.net/manual/en/memcached.configuration.php

EOF

# default options with description from upstream
cat NTS/memcached.ini >>%{pecl_name}.ini

%if %{with_zts}
cp -r NTS ZTS
%endif


%build
peclconf() {
%configure --enable-memcached-igbinary \
           --enable-memcached-json \
           --enable-memcached-sasl \
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
           --enable-memcached-protocol \
%endif
           --with-php-config=$1
}
cd NTS
%{_bindir}/phpize
peclconf %{_bindir}/php-config
make %{?_smp_mflags}

%if %{with_zts}
cd ../ZTS
%{_bindir}/zts-phpize
peclconf %{_bindir}/zts-php-config
make %{?_smp_mflags}
%endif


%install
# Install the NTS extension
make install -C NTS INSTALL_ROOT=%{buildroot}

# Drop in the bit of configuration
# rename to z-memcached to be load after msgpack
install -D -m 644 %{pecl_name}.ini %{buildroot}%{php_inidir}/z-%{pecl_name}.ini

# Install XML package description
install -D -m 644 package.xml %{buildroot}%{pecl_xmldir}/%{name}.xml

# Install the ZTS extension
%if %{with_zts}
make install -C ZTS INSTALL_ROOT=%{buildroot}
install -D -m 644 %{pecl_name}.ini %{buildroot}%{php_ztsinidir}/z-%{pecl_name}.ini
%endif

# Test & Documentation
cd NTS
for i in $(grep 'role="test"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_testdir}/%{pecl_name}/$i
done
for i in $(grep 'role="doc"' ../package.xml | sed -e 's/^.*name="//;s/".*$//')
do install -Dpm 644 $i %{buildroot}%{pecl_docdir}/%{pecl_name}/$i
done


%post
%{pecl_install} %{pecl_xmldir}/%{name}.xml >/dev/null || :


%postun
if [ $1 -eq 0 ] ; then
    %{pecl_uninstall} %{pecl_name} >/dev/null || :
fi


%check
OPT="-n"
[ -f %{php_extdir}/igbinary.so ] && OPT="$OPT -d extension=igbinary.so"
[ -f %{php_extdir}/json.so ]     && OPT="$OPT -d extension=json.so"
[ -f %{php_extdir}/msgpack.so ]  && OPT="$OPT -d extension=msgpack.so"

: Minimal load test for NTS extension
%{__php} $OPT \
    -d extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}

%if %{with_zts}
: Minimal load test for ZTS extension
%{__ztsphp} $OPT \
    -d extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep %{pecl_name}
%endif

%if %{with_tests}
ret=0

: Launch the Memcached service
memcached -p 11211 -U 11211      -d -P $PWD/memcached.pid

: Run the upstream test Suite for NTS extension
pushd NTS
rm tests/flush_buffers.phpt tests/touch_binary.phpt
TEST_PHP_EXECUTABLE=%{__php} \
TEST_PHP_ARGS="$OPT -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__php} -n run-tests.php || ret=1
popd

%if %{with_zts}
: Run the upstream test Suite for ZTS extension
pushd ZTS
rm tests/flush_buffers.phpt tests/touch_binary.phpt
TEST_PHP_EXECUTABLE=%{__ztsphp} \
TEST_PHP_ARGS="$OPT -d extension=$PWD/modules/%{pecl_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__ztsphp} -n run-tests.php || ret=1
popd
%endif

# Cleanup
if [ -f memcached.pid ]; then
   kill $(cat memcached.pid)
fi

exit $ret
%endif


%files
%doc %{pecl_docdir}/%{pecl_name}
%doc %{pecl_testdir}/%{pecl_name}
%{pecl_xmldir}/%{name}.xml

%config(noreplace) %{php_inidir}/z-%{pecl_name}.ini
%{php_extdir}/%{pecl_name}.so

%if %{with_zts}
%config(noreplace) %{php_ztsinidir}/z-%{pecl_name}.ini
%{php_ztsextdir}/%{pecl_name}.so
%endif


%changelog
* Thu Oct 09 2014 Andy Thompson <andy@webtatic.com> - 2.2.0-2
- Add support for libmemcached10 on < EL7

* Sun Sep 14 2014 Andy Thompson <andy@webtatic.com> - 2.2.0-1
- Import EPEL php-pecl-memcached-2.2.0-1.el7 RPM
- Remove msgpack dependency
