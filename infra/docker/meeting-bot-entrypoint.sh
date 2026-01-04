#!/bin/bash
set -e

# Clean stale dbus pid
rm -f /var/run/dbus/pid

# Start dbus if not running
if [ ! -e /var/run/dbus/system_bus_socket ]; then
    dbus-daemon --system --fork
fi

# Initialize dbus session for the user if needed (often handled by autolaunch, but we can try)
# export DBUS_SESSION_BUS_ADDRESS=`dbus-daemon --fork --config-file=/usr/share/dbus-1/session.conf --print-address`

echo "[Entrypoint] Starting Meeting Bot..."
exec "$@"
