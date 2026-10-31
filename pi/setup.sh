#!/bin/sh
# Run as root on a Raspberry Pi OS (Lite is fine) from the "Classroom Python" folder:
#   sudo ./pi/setup.sh [SSID] [WIFI_PASSPHRASE]
# Makes the Pi a closed Wi-Fi network (192.168.4.1) that serves the Classroom Python page on port 80.
# Python is the only dependency; no internet is needed after the apt step.
set -eu
SSID="${1:-PythonClass}"
PASS="${2:-pythonclass}"   # 8+ characters; change it!
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
HERE="$(cd "$(dirname "$0")/.." && pwd)"

apt-get update
apt-get install -y hostapd dnsmasq python3 util-linux

# --- app ---
id classroom >/dev/null 2>&1 || useradd --system --home /var/lib/classroom-python --shell /usr/sbin/nologin classroom
mkdir -p /opt/classroom-python /var/lib/classroom-python
cp -r "$HERE/server" "$HERE/web" /opt/classroom-python/
chown -R classroom:classroom /var/lib/classroom-python
cp "$HERE/pi/classroom-python.service" /etc/systemd/system/

# --- Wi-Fi access point (wlan0, static 192.168.4.1) ---
cat > /etc/hostapd/hostapd.conf <<EOC
interface=wlan0
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
wpa=2
wpa_passphrase=$PASS
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOC
sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

# dnsmasq: DHCP for the tablets + every name resolves to the Pi, so "python.class" (or anything) works
cat > /etc/dnsmasq.d/classroom.conf <<EOC
interface=wlan0
bind-interfaces
dhcp-range=192.168.4.20,192.168.4.200,255.255.255.0,12h
address=/#/192.168.4.1
EOC

# static address for wlan0 (dhcpcd on older Raspberry Pi OS; NetworkManager on Bookworm+)
if command -v nmcli >/dev/null 2>&1 && systemctl is-active --quiet NetworkManager; then
  nmcli connection delete classroom-ap >/dev/null 2>&1 || true
  nmcli connection add type ethernet ifname wlan0 con-name classroom-ap ipv4.method manual ipv4.addresses 192.168.4.1/24 >/dev/null
  nmcli device set wlan0 managed no || true
  echo "NOTE: if wlan0 does not come up with 192.168.4.1, set it manually (see README)."
else
  grep -q 'classroom-ap' /etc/dhcpcd.conf 2>/dev/null || cat >> /etc/dhcpcd.conf <<EOC

# classroom-ap
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOC
fi

rfkill unblock wlan 2>/dev/null || true
systemctl unmask hostapd
systemctl daemon-reload
systemctl enable --now classroom-python hostapd dnsmasq

echo
echo "Done. Reboot, join Wi-Fi '$SSID' on a tablet and open http://192.168.4.1/"
echo "Teacher page: http://192.168.4.1/admin.html   PIN: $(cat /var/lib/classroom-python/admin_pin.txt 2>/dev/null || echo '(shown after first start: cat /var/lib/classroom-python/admin_pin.txt)')"
