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
| Sync Word | 0x1424 | Reticulum standard |
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


