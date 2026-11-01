#!/bin/sh
# Update the Classroom Python app on the Pi WITHOUT touching Wi-Fi/hotspot settings.
# Run as root from the "Classroom Python" folder after pulling or copying in the new code:
#   sudo ./pi/update.sh
# Only copies server/ and web/ to /opt/classroom-python, refreshes the systemd unit and restarts the
# service. The teacher PIN and tablet/Pi mode (in /var/lib/classroom-python) are kept.
# For first-time install or Wi-Fi changes use pi/setup.sh instead.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
HERE="$(cd "$(dirname "$0")/.." && pwd)"
[ -d "$HERE/server" ] && [ -d "$HERE/web" ] || { echo "server/ and web/ not found in $HERE"; exit 1; }
[ -d /opt/classroom-python ] || { echo "Not installed yet: run pi/setup.sh first"; exit 1; }

systemctl stop classroom-python || true
rm -rf /opt/classroom-python/server /opt/classroom-python/web
cp -r "$HERE/server" "$HERE/web" /opt/classroom-python/
rm -rf /opt/classroom-python/server/data /opt/classroom-python/server/__pycache__
chown -R root:root /opt/classroom-python
chmod 755 /opt/classroom-python
chmod -R u=rwX,go=rX /opt/classroom-python
cp "$HERE/pi/classroom-python.service" /etc/systemd/system/
systemctl daemon-reload
systemctl start classroom-python
sleep 2
if systemctl is-active --quiet classroom-python; then
  echo "classroom-python updated and running. Wi-Fi was not touched."
else
  echo "WARNING: classroom-python did not start. Details:"
  systemctl status classroom-python --no-pager -l | tail -15 || true
  journalctl -u classroom-python -n 20 --no-pager || true
  exit 1
fi
