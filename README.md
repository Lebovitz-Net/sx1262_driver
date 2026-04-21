# Introduction

The **sx1262_driver** project provides a clean, maintainable, and hardware‑accurate Python driver for the Semtech **SX1262** LoRa transceiver. Unlike many hobby‑grade libraries, this driver is built with **architectural rigor**, **predictable timing**, and **explicit separation of concerns**, making it suitable for real‑world mesh networking, experimentation, and educational use.

The driver targets **Raspberry Pi** devices running Linux, where the required low‑level interfaces—**SPI**, **GPIO**, and **IRQ‑driven event handling**—are available and behave consistently. Windows and macOS environments do not expose the necessary hardware layers, so all building, testing, and hardware‑in‑the‑loop development must be performed on a Pi.

At its core, the driver provides:

- A **minimal, explicit API** for configuring and controlling the SX1262  
- A **robust IRQ/event loop** that cleanly separates hardware events from application logic  
- Safe handling of **busy states**, **FIFO operations**, and **transitional IRQ conditions**  
- A structure that encourages **readability**, **testability**, and **future extension** (e.g., higher‑level mesh protocols)

The project includes example scripts demonstrating basic transmit/receive flows, along with a reproducible build workflow for packaging and installing the driver on a Raspberry Pi.

## Building the driver
You must build the driver on a raspberry pi device. This is the intended target.

To build this driver. use the following steps

### install required system packages

sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential

### Install the back end
pip install --upgrade build

### Clone the repo onto the Raspberry Pi device
git clone https://github.com/Lebovitz-Net/sx1262_driver.git
cd sx1262_driver

### Project structure looks like this
sx1262_driver/
    pyproject.toml
    README.md
    LICENSE
    sx1262_driver/
        __init__.py
        ...
    examples/
    scripts/

### Build the package
python3 -m build

The project will produce the folling

dist/
    sx1262_driver-<version>.tar.gz
    sx1262_driver-<version>-py3-none-any.whl

### Install the package on the Pi

#### Install the Wheel
pip install dist/sx1262_driver-*-py3-none-any.whl

#### Or Install the source distribution
pip install dist/sx1262_driver-*.tar.gz

### Verify Installation
python3
from sx1262_driver import SX1262
radio = SX1262()
## Run the examples
python3 examples/listener.py
python3 examples/tx.py

#### these import the installed Package
from sx1262_driver import SX1262

## Install directly from GitHub
You can also install the package directly from this repository (useful for CI or testing):

```bash
pip install git+https://github.com/Lebovitz-Net/sx1262_driver.git
```

## Reticulum support
The package includes an optional Reticulum interface implementation in `sx1262_driver.reticulum_interface`.

### Install with Reticulum support

Install the package with the optional `reticulum` extra, which pulls in the `rns` dependency:

```bash
pip install "sx1262_driver[reticulum]"
```

To install directly from GitHub:

```bash
pip install "git+https://github.com/Lebovitz-Net/sx1262_driver.git#egg=sx1262_driver[reticulum]"
```

To install from a local clone (editable, useful during development):

```bash
pip install -e ".[reticulum]"
```

### Set up the Reticulum interface

After installation, run the provided console script to:

1. Install the interface loader file into `~/.reticulum/interfaces/`
2. Create a starter `~/.reticulum/config` (skipped if the file already exists)

```bash
sx1262-install-rns-interface
```

The generated config includes a TCP backbone entry (`rns.noderage.org:4242`) and a pre-filled `[[SX1262 LoRa Interface]]` section with default mesh parameters:

| Parameter | Default | Notes |
|---|---|---|
| Frequency | 914.875 MHz | North American LoRa mesh |
| Bandwidth | 125 kHz | |
| Spreading Factor | SF9 | |
| Coding Rate | 4/5 | |
| Sync Word | 0x1424 | Reticulum standard; also used as the MeshCore "private" sync word — ensures interoperability between Reticulum and MeshCore nodes on the same channel |
| Preamble | 18 symbols | Minimum for RNode compatibility |

Adjust the GPIO pin assignments (`reset_pin`, `busy_pin`, `nss_pin`) in `~/.reticulum/config` for your specific wiring.

### Start Reticulum

```bash
rnsd
```

Reticulum will load the SX1262 interface automatically from the config file.

### IRQ vs polling mode

- `irq_pin = -1` and `use_irq = false` (default): polling mode, no IRQ wiring required
- Set `irq_pin` to your DIO1 BCM pin and `use_irq = true` to enable interrupt-driven receive

### Running rnsd as a system service

An example systemd unit file is provided at `examples/rnsd.service`. It references the user venv at `/home/gregg/.venv` — adjust `User` and `ExecStart` if your username or venv path differs.

```bash
sudo cp examples/rnsd.service /etc/systemd/system/rnsd.service
# edit User and ExecStart if needed
sudo systemctl daemon-reload
sudo systemctl enable rnsd
sudo systemctl start rnsd
sudo journalctl -u rnsd -f   # follow logs
```

The venv binary has a shebang pointing to the venv Python, so all venv packages (including `sx1262_driver` and `rns`) are available without activating the venv first.

---

## Interface discovery (rmap.world)

Reticulum 1.1+ includes a built-in [discoverable interfaces](https://reticulum.network/manual/interfaces.html#discoverable-interfaces) system that periodically broadcasts a signed announce packet containing your node's connection details, location, and radio parameters. Community map sites such as [rmap.world](https://rmap.world) listen for these announces and display discovered nodes automatically — no collector hash or Sideband required.

> **Note:** Interface discovery requires the `lxmf` package to be installed (`pip install lxmf`).

### How it works

When `discoverable = yes` is set on an interface, `rnsd` will:

1. Generate a proof-of-work cryptographic stamp for the interface (cached after first run)
2. Broadcast a discovery announce over the network at the configured `announce_interval`
3. Automatically configure the interface in `gateway` or `access_point` mode if not explicitly set

Peers (and map aggregators like rmap.world) receive these announces via the standard `rnstransport.discovery.interface` destination and can auto-connect or display the node.

### Configuration

Add the following options to your `[[SX1262 LoRa Interface]]` block in `~/.reticulum/config`:

```ini
[[SX1262 LoRa Interface]]
  type = SX1262Interface
  enabled = yes
  # ... existing radio parameters ...

  # Enable interface discovery
  discoverable = yes
  discovery_name = My LoRa Node
  announce_interval = 360        # minutes between announces (default 360)

  # Physical location (decimal degrees / meters) — displayed on rmap.world
  latitude  = 42.9956
  longitude = -71.4548
  height    = 50

  # Radio parameters broadcast to peers
  discovery_frequency = 914875000   # Hz
  discovery_bandwidth = 125000      # Hz
```

| Option | Description |
|---|---|
| `discoverable` | `yes` to enable; triggers gateway/AP mode automatically |
| `discovery_name` | Human-readable label shown on the map |
| `announce_interval` | Minutes between announces (minimum 5) |
| `latitude` / `longitude` / `height` | Decimal degrees and meters; used for map placement |
| `discovery_frequency` | Operating frequency in Hz |
| `discovery_bandwidth` | Signal bandwidth in Hz |
| `discovery_stamp_value` | Proof-of-work difficulty (default 14; higher = more CPU, more spam-resistant) |

### Custom interface note

The `SX1262Interface` explicitly sets `self.supports_discovery = True` so that the RNS discovery loop includes it. The base `Interface` class defaults this to `False`; only built-in types like `RNodeInterface` and `TCPInterface` set it automatically.

### Checking status

After restarting `rnsd`, confirm the interface is in gateway mode:

```bash
rnstatus
```

You should see `Mode : Gateway` on the SX1262 interface. The first announce fires after the initial proof-of-work stamp is computed (a few seconds on modern hardware). Subsequent announces respect `announce_interval`.

---

## MeshCore compatibility

The SX1262 driver can also communicate with [MeshCore](https://meshcore.co.uk) nodes. MeshCore uses a different frequency and radio configuration from Reticulum, but shares the same LoRa sync word (`LORA_SYNC_WORD_PRIVATE = 0x1424`), which allows both stacks to coexist on hardware that can be reconfigured.

The parameters below are taken from `examples/listener.py` and match the MeshCore default channel plan for North America:

| Parameter | Value | Notes |
|---|---|---|
| Frequency | 910.525 MHz | MeshCore North America default |
| Bandwidth | 62.5 kHz | Narrower than Reticulum |
| Spreading Factor | SF7 | Shorter range, higher throughput |
| Coding Rate | 4/5 | |
| Sync Word | 0x1424 (`LORA_SYNC_WORD_PRIVATE`) | Same as Reticulum — shared private network |
| RX Timeout | `RX_CONTINUOUS` | Listen continuously |

To use the driver with MeshCore parameters, configure the `SX1262` instance as shown in `examples/listener.py`:

```python
from sx1262_driver.sx1262_constants import *
from sx1262_driver.sx1262 import SX1262

radio = SX1262(
    spi_bus=0, spi_device=0,
    reset_pin=18, busy_pin=20, nss_pin=21
)
radio.begin(
    freq=910525000,
    bw=62500,
    sf=7,
    cr=5,
    sync_word=LORA_SYNC_WORD_PRIVATE,
)
```

> **Note:** The Reticulum interface (`rnsd`) uses different radio parameters (914.875 MHz, 125 kHz BW, SF9). You cannot run both stacks simultaneously on a single radio — each requires its own `SX1262` instance or a full reconfiguration between modes.


