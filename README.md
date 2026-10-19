# Balena Wi-Fi Setup — Super Robust Captive Portal Tool

This folder provides a **rock-solid, production-grade Wi-Fi configuration system** powered by **[`balena-io/wifi-connect`](https://github.com/balena-os/wifi-connect)** instead of fragile `nmcli` shell commands.

It is completely self-contained within this directory and can be deployed directly onto any Raspberry Pi, Debian, or Ubuntu system.

---

## 🚀 Why `balena-io/wifi-connect` over raw `nmcli`?

| Feature | Raw `nmcli` Approach | `balena-io/wifi-connect` (This System) |
| :--- | :--- | :--- |
| **Captive Portal** | ❌ None. User must manually type `http://10.42.0.1:8080/wifi` into browser. | ✅ **Native Captive Portal**. Intercepts DNS queries; phones (iOS & Android) automatically trigger *"Sign in to Wi-Fi"* modal. |
| **Communication** | ⚠️ Fragile shell `subprocess` calling CLI commands and parsing stdout strings. | ✅ **Direct NetworkManager D-Bus integration** in compiled Rust for high reliability and speed. |
| **Fallback on Failure** | ⚠️ Complex script state machine prone to race conditions and lockouts if password wrong. | ✅ **Automated AP Restoration**. If target network connection fails or credentials reject, AP restores instantly so user isn't stranded. |
| **Network Scanning** | ❌ Manual rescan triggers with periodic blocking and polling. | ✅ **REST API (`/networks`)** provides real-time scanned SSIDs, RSSI dBm signal strength, and security modes. |
| **Root & Polkit Permissions** | ⚠️ Frequent polkit permission errors or sudo password prompt blocks. | ✅ Clean daemon architecture handling privileged NetworkManager access safely. |

---

## ⚡ Prerequisites on Raspberry Pi / Linux

1. **Linux NetworkManager**
2. **Python ≥ 3.9** with `flask` (or `uv`):
   ```bash
   pip install -r requirements.txt
   # or: sudo apt install python3-flask
   ```
3. **Balena `wifi-connect` binary**:
   Run the included installer to automatically download the official precompiled binary matching your architecture (`aarch64`, `armv7l`, or `x86_64`):
   ```bash
   ./install.sh
   # or via Python:
   python3 wifi_setup.py --install
   ```

---

## 📱 How to Run

### Option 1: Access Point & Captive Portal Mode (Phone Connects to Pi)
```bash
# Using Python:
python3 wifi_setup.py

# Or using launcher:
./run.sh
```

1. **Connect your phone** to Wi-Fi SSID **`hermes`** (Password: **`12345678`**).
2. **Instant Captive Portal**: Your phone will automatically display the Wi-Fi setup page.
   *(Or navigate manually to `http://192.168.42.1:80` or `http://192.168.42.1:8080/wifi`)*.
3. **Sign in to Superadmin Security Modal**:
   - **User ID**: `superadmin`
   - **Password**: `Gluvok@241821`
4. Pick from the **live scanned Wi-Fi networks** (with real signal bars) or enter custom SSID, input your password, and click **Save & Connect**.
5. The device connects to your Wi-Fi, saves credentials into the persistent SQLite vault, and shuts down the hotspot.

---

### Option 2: Connect Directly to Existing Phone Hotspot
```bash
python3 wifi_setup.py --connect --ssid "MyPhoneHotspot" --password "mypassword"
```
*(Leave out `--ssid` and `--password` to be prompted interactively).*

---

## 📁 Architecture Overview

```text
balena wifi/
├── bin/                    # Local wifi-connect binary storage (auto-downloaded)
├── constants.py            # AP SSIDs, gateways, timeouts, ports, and paths
├── installer.py            # Detects CPU architecture and downloads official balena release
├── balena_driver.py        # Balena process supervisor, REST client, and simulation runner
├── hotspot.py              # AP creation, lifecycle, and network discovery
├── connection.py           # Client connection handshake with auto-fallback
├── watchdog.py             # Background connection watchdog with flap-debounce protection
├── auth.py                 # Superadmin credentials and token security
├── vault.py                # Persistent SQLite database (wifi_vault.db)
├── server.py               # Flask management console runner
├── routes.py               # Web endpoints and OS captive portal probes (/generate_204, etc.)
├── templates/wifi.html     # Responsive dark-mode portal with live signal meter
├── ui/index.html           # Native captive portal UI bundle for wifi-connect -u
├── wifi_setup.py           # Standalone CLI entry point
├── install.sh              # One-click architecture-aware installer
├── run.sh                  # One-click runner script
└── tests/                  # Pytest unit and integration test suite
```

---

## 🛡️ Robustness & Watchdog Guard

- **Flap Prevention**: Watchdog requires consecutive failed network checks before engaging the emergency captive portal, avoiding false positives from intermittent drops.
- **Race Condition Prevention**: Employs connection locks (`is_connecting()`) and re-entrant synchronization to guarantee the watchdog never interrupts active handshakes.
- **Persistent Vault**: All connected SSIDs and credentials are saved to `wifi_vault.db` and can be clicked to quickly reconnect.
- **Simulation Mode**: Works seamlessly on development machines (macOS/Windows) for testing UI, API, and routes without requiring Linux NetworkManager.
