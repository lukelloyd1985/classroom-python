# Classroom Python

A no-login Python editor for tablets on a closed Wi-Fi network served by a Raspberry Pi.
Students open one page, type Python, press Run. The teacher can switch, mid-lesson, **where the code runs**:

| | **Tablet mode** (Skulpt in the browser) | **Pi mode** (real CPython on the Pi) |
|---|---|---|
| Load on the Pi | none (static files only) | one short-lived process per Run |
| Python | Python 3 subset (Skulpt 1.0: no f-strings, small stdlib) | full Python 3 + stdlib |
| Works on very old browsers | yes (ES5 build, tested for ES5 syntax) | yes (plain XHR + polling) |
| Isolation between students | automatic (own device) | separate process and temp folder per tablet |
| Endless loop | stops after 15 s, or press Stop | stops after 10 s CPU, or press Stop |

No accounts, no grading, no quiz features. Each tablet keeps its own code in browser storage (`localStorage`).

## Run it on any computer (to try it)

```sh
cd "Classroom Python/server"
python3 server.py --port 8000          # prints the teacher PIN
```
Students: `http://<pi-address>:8000/`   Teacher: `http://<pi-address>:8000/admin.html`

Python 3.7+ standard library only: nothing to `pip install`.

## Switching mode during class

Open `/admin.html`, enter the PIN, tap **On each tablet** or **On the Pi**. Tablets follow within ~5 seconds
(a run already in progress finishes where it started). The choice survives restarts.
The same page shows how many runs are active on the Pi and has a **Stop all** button.

**Changing the PIN:** on the Pi, edit the PIN file and restart the service (the file is read only at start-up):

```sh
echo "7391" | sudo tee /var/lib/classroom-python/admin_pin.txt
sudo systemctl restart classroom-python
```
Any text works (surrounding whitespace is ignored). Keep the file readable by the `classroom` user
(`sudo chown classroom:classroom /var/lib/classroom-python/admin_pin.txt`). An empty file makes the server
generate a new random PIN. `--pin` or `CLASSROOM_PIN`, if used, override the file. Restarting stops any programs
running on the Pi at that moment but keeps the chosen mode.

Tablets that cannot run Skulpt at all automatically use the Pi instead and show a note.
For testing one tablet, add `?mode=client` or `?mode=server` to its address (the teacher flag is then ignored on that tablet).

## Getting Raspberry Pi OS onto the Pi (do this first)

`pi/setup.sh` expects a Pi that is already running Raspberry Pi OS, has a network connection to the internet
(only for the one-off `apt` install) and that you can reach by SSH or keyboard and screen.

**You need:** a Raspberry Pi with built-in Wi-Fi (3B+, 4, 5 or Zero 2 W; a 4 or 5 is comfortable for a full class),
a microSD card of 16 GB or more, a suitable power supply, and a computer with an SD card reader.
Use an Ethernet cable for the setup if you can, because the Wi-Fi radio becomes the classroom hotspot afterwards.

1. **Install Raspberry Pi Imager** on your computer from <https://www.raspberrypi.com/software/> and insert the SD card.
2. In Imager choose your Pi model, then the OS **Raspberry Pi OS Lite (64-bit)** (under "Raspberry Pi OS (other)").
   Lite has no desktop, which is all this needs. Choose the SD card as storage.
3. When asked to customise settings (the gear icon or "Edit settings", depending on the version), set:
   * **Hostname**, for example `pythonpi`
   * **Username and password** (this is your admin login, not a student or teacher PIN)
   * **Wi-Fi** name and password of a network that has internet, *only if* you are not using Ethernet
   * **Locale/time zone** and keyboard layout
   * **Enable SSH** (password authentication is fine)
4. Write the card, put it in the Pi and power it on. The first boot takes a minute or two.
5. **Connect to it** from your computer: `ssh <username>@pythonpi.local` (or use the Pi's IP address from your router,
   or plug in a keyboard and screen). Then bring it up to date:
   ```sh
   sudo apt update && sudo apt full-upgrade -y
   ```
6. **Get this project onto the Pi**, either with git (while it has internet):
   ```sh
   sudo apt install -y git
   git clone https://github.com/lukelloyd1985/useful.git
   cd "useful/Classroom Python"
   ```
   or copy the folder from your computer: `scp -r "Classroom Python" <username>@pythonpi.local:~/`
7. Continue with **Raspberry Pi setup** below.

After `setup.sh` the Wi-Fi radio is the classroom hotspot and no longer joins your normal network, so afterwards
reach the Pi by Ethernet, or join your laptop to the classroom Wi-Fi and use `ssh <username>@192.168.4.1`.
Have the Ethernet cable or a keyboard and screen handy the first time in case something needs fixing.

Check the Python version before you start: `python3 --version` should show 3.7 or newer. Current Raspberry Pi OS does.

## Raspberry Pi setup

Run these on the Pi, from the `Classroom Python` folder:

```sh
sudo ./pi/setup.sh PythonClass "a-good-passphrase"
sudo reboot
```
This installs `hostapd` + `dnsmasq`, makes the Pi a Wi-Fi network at `192.168.4.1`
(every DNS name resolves to the Pi, so tablets can type anything), and installs the
`classroom-python` systemd service on port 80 running as an unprivileged `classroom` user.
The PIN is in `/var/lib/classroom-python/admin_pin.txt`.
Review the script before running it on a Pi you care about; it edits Wi-Fi and DNS configuration.
Network-manager setups differ between Raspberry Pi OS releases, so check `ip addr show wlan0` shows `192.168.4.1`
and set that address manually if not.

## Pi mode limits and safety

Student programs run as subprocesses with: 10 s CPU, 384 MB memory, 1 MB per written file, 64 open files,
5 min wall clock, 100 KB of output, a throwaway working folder, a stripped environment, and (when the OS allows
`unshare -rn`) no network. At most 16 run at once (`--max-procs`); more get a friendly "busy" message.
A tablet that disappears has its program killed after ~20 s. Tune with `--cpu-seconds`, `--memory-mb`, `--max-procs`, etc. (`server.py --help`).

Be aware: this is resource limiting, not a hardened jail. All runs share one Linux user, so a determined
student could look at another student's temp folder. That is acceptable for a closed classroom; for stronger
isolation put `bwrap`/`nsjail`/containers around the command in `Manager.start`.

## Layout

```
server/server.py        API + static server (stdlib only)
server/test_server.py   `python3 -m unittest test_server` (runs, input, limits, isolation, admin)
web/index.html, app.js  student page (ES5 only)
web/admin.html          teacher controls
web/vendor/             Skulpt 1.0.0 (MIT), CodeMirror 5.65 (MIT) - no CDN needed offline
pi/                     setup script and systemd unit
```

## Known gaps

* Skulpt 1.0.0 is used because newer Skulpt builds are not ES5 and would not parse on Android 4.2.
  Its biggest gap for students is **f-strings** (the page shows a hint); `turtle` graphics are not wired into the page.
* The "Colours" button turns on CodeMirror syntax highlighting. It is off by default because some old Android
  soft keyboards misbehave in rich editors; the plain text box always works.
* Not yet tested on a real Android 4.2 tablet - try one before the first lesson (including the on-screen keyboard).
