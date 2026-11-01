#!/bin/sh
# Run as root on Raspberry Pi OS (Lite is fine) from the "Classroom Python" folder:
#   sudo ./pi/setup.sh [SSID] [WIFI_PASSPHRASE] [WIFI_COUNTRY e.g. GB]
# Makes the Pi a closed Wi-Fi network (192.168.4.1) that serves the Classroom Python page on port 80.
#
# Two paths, chosen automatically:
#   * NetworkManager (Raspberry Pi OS Bookworm and newer): a NetworkManager Wi-Fi hotspot
#     (NetworkManager runs its own DHCP/DNS for it, so hostapd/dnsmasq are NOT used)
#   * otherwise (Bullseye and older): hostapd + dnsmasq + dhcpcd
#
# WARNING: wlan0 becomes the hotspot and stops joining other Wi-Fi. If you are connected by SSH over
# Wi-Fi the session will drop. Use Ethernet or a keyboard and screen while running this.
set -eu
SSID="${1:-PythonClass}"
PASS="${2:-pythonclass}"   # 8+ characters; change it!
COUNTRY="${3:-}"
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
[ "${#PASS}" -ge 8 ] || { echo "Wi-Fi passphrase must be at least 8 characters"; exit 1; }
HERE="$(cd "$(dirname "$0")/.." && pwd)"

if command -v nmcli >/dev/null 2>&1 && systemctl is-active --quiet NetworkManager; then
  USE_NM=1
else
  USE_NM=0
fi

apt-get update
if [ "$USE_NM" = 1 ]; then
  apt-get install -y python3 util-linux
else
  apt-get install -y hostapd dnsmasq python3 util-linux
fi

# --- app ---
id classroom >/dev/null 2>&1 || useradd --system --home /var/lib/classroom-python --shell /usr/sbin/nologin classroom
mkdir -p /opt/classroom-python /var/lib/classroom-python
# Fresh copy each run (no stale files). Permissions are set explicitly: cp keeps the source folder's
# modes, and a private (700) project folder would stop the "classroom" user entering /opt/classroom-python.
rm -rf /opt/classroom-python/server /opt/classroom-python/web
cp -r "$HERE/server" "$HERE/web" /opt/classroom-python/
rm -rf /opt/classroom-python/server/data /opt/classroom-python/server/__pycache__
chown -R root:root /opt/classroom-python
chmod 755 /opt/classroom-python
chmod -R u=rwX,go=rX /opt/classroom-python
chown -R classroom:classroom /var/lib/classroom-python
chmod 750 /var/lib/classroom-python
cp "$HERE/pi/classroom-python.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable classroom-python
systemctl restart classroom-python
sleep 2
if systemctl is-active --quiet classroom-python; then
  echo "classroom-python service is running."
else
  echo "WARNING: classroom-python did not start. Details:"
  systemctl status classroom-python --no-pager -l | tail -15 || true
  journalctl -u classroom-python -n 20 --no-pager || true
fi

# --- clean slate: remove Wi-Fi/hotspot config from any earlier run so re-running always ends the same ---
# Deletes: every NetworkManager Wi-Fi profile, anything bound to wlan0 (e.g. the wrong "ethernet" profile an
# early version created) and the files/services both setup methods write. Wired profiles are left alone.
clean_wifi_config() {
  echo "Cleaning old Wi-Fi configuration..."
  for svc in hostapd dnsmasq; do
    systemctl disable --now "$svc" >/dev/null 2>&1 || true
  done
  if command -v nmcli >/dev/null 2>&1 && systemctl is-active --quiet NetworkManager; then
    nmcli -t -f UUID,TYPE connection show 2>/dev/null | while IFS=: read -r uuid ctype; do
      [ -n "$uuid" ] || continue
      iface="$(nmcli -g connection.interface-name connection show uuid "$uuid" 2>/dev/null || true)"
      if [ "$ctype" = "802-11-wireless" ] || [ "$iface" = "wlan0" ]; then
        nmcli connection delete uuid "$uuid" >/dev/null 2>&1 || true
      fi
    done
    nmcli connection delete classroom-ap >/dev/null 2>&1 || true
    nmcli device set wlan0 managed yes >/dev/null 2>&1 || true   # an early version set it to "no"
  fi
  rm -f /etc/NetworkManager/dnsmasq-shared.d/classroom.conf /etc/dnsmasq.d/classroom.conf /etc/hostapd/hostapd.conf
  if [ -f /etc/dhcpcd.conf ]; then
    sed -i '/^# classroom-ap$/,/^    nohook wpa_supplicant$/d' /etc/dhcpcd.conf
  fi
  ip addr flush dev wlan0 >/dev/null 2>&1 || true
}
clean_wifi_config

# --- Wi-Fi regulatory country: the radio stays blocked until one is set ---
if [ -n "$COUNTRY" ]; then
  if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_wifi_country "$COUNTRY" || true
  else
    iw reg set "$COUNTRY" 2>/dev/null || true
  fi
else
  echo "NOTE: no Wi-Fi country given. If the hotspot does not start, run: sudo raspi-config nonint do_wifi_country GB"
  echo "      (use your own 2-letter country code) or pass it as the third argument to this script."
fi
rfkill unblock wlan 2>/dev/null || true

if [ "$USE_NM" = 1 ]; then
  # ---------- NetworkManager hotspot ----------
  # Every DNS name resolves to the Pi, so tablets can type anything (picked up by NM's own dnsmasq).
  mkdir -p /etc/NetworkManager/dnsmasq-shared.d
  echo "address=/#/192.168.4.1" > /etc/NetworkManager/dnsmasq-shared.d/classroom.conf

  nmcli radio wifi on
  # wifi-sec.pmf disable: the Pi 3's brcmfmac Wi-Fi driver fails to start the AP with PMF
  # ("key setting validation failed"). WPA+WPA2 with TKIP+AES (not RSN/CCMP only): the Android 4.2 tablets
  # failed the handshake (AP-STA-POSSIBLE-PSK-MISMATCH) with a strict WPA2/AES-only network.
  nmcli connection add type wifi ifname wlan0 con-name classroom-ap autoconnect yes ssid "$SSID" \
    802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASS" wifi-sec.proto wpa,rsn wifi-sec.pairwise tkip,ccmp wifi-sec.group tkip,ccmp wifi-sec.pmf disable \
    ipv4.method shared ipv4.addresses 192.168.4.1/24 ipv6.method disabled
  nmcli connection up classroom-ap || echo "Could not start the hotspot yet - see the README troubleshooting section."
else
  # ---------- hostapd + dnsmasq + dhcpcd ----------
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

  cat > /etc/dnsmasq.d/classroom.conf <<EOC
interface=wlan0
bind-interfaces
dhcp-range=192.168.4.20,192.168.4.200,255.255.255.0,12h
address=/#/192.168.4.1
EOC

  grep -q 'classroom-ap' /etc/dhcpcd.conf 2>/dev/null || cat >> /etc/dhcpcd.conf <<EOC

# classroom-ap
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOC
  systemctl unmask hostapd
  systemctl enable --now hostapd dnsmasq
fi

echo
echo "Done. Reboot, join Wi-Fi '$SSID' on a tablet and open http://192.168.4.1/"
echo "Teacher page: http://192.168.4.1/admin.html   PIN: $(cat /var/lib/classroom-python/admin_pin.txt 2>/dev/null || echo '(cat /var/lib/classroom-python/admin_pin.txt)')"
