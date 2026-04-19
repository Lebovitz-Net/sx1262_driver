#!/usr/bin/env python3
"""
sx1262-telemetry-beacon: Broadcast a fixed GPS coordinate as Reticulum/LXMF
telemetry in Sideband-compatible format (visible on meshmap.reticulum.network).

Requires: rns, lxmf  (pip install rns lxmf)
These are already installed when you install sx1262_driver[reticulum].

Usage:
    sx1262-telemetry-beacon --lat 37.7749 --lon -122.4194 --alt 50 \\
                            --name "MyPi" --collector <hex_hash> --interval 300
"""

import os
import sys
import time
import struct
import signal
import argparse
import threading

import RNS
import LXMF
import RNS.vendor.umsgpack as umsgpack

# Sensor IDs (from Sideband/sbapp/sideband/sense.py)
SID_TIME     = 0x01
SID_LOCATION = 0x02

IDENTITY_FILENAME = "telemetry_beacon_identity"
LXMF_STORAGE_DIR  = "lxmf_beacon"


def pack_telemetry(lat: float, lon: float, alt: float) -> bytes:
    """
    Pack time + location into the Sideband-compatible binary telemetry format.

    The packed dict layout mirrors Telemeter.packed() from sense.py:
      {SID_TIME: int_utc, SID_LOCATION: [struct_bytes * 6 + int_timestamp]}
    """
    now = int(time.time())
    location = [
        struct.pack("!i", int(round(lat, 6) * 1e6)),   # latitude  × 1e6 (signed)
        struct.pack("!i", int(round(lon, 6) * 1e6)),   # longitude × 1e6 (signed)
        struct.pack("!i", int(round(alt, 2) * 1e2)),   # altitude  × 1e2 (signed)
        struct.pack("!I", 0),                           # speed (unsigned), 0 = stationary
        struct.pack("!i", 0),                           # bearing (signed), 0 = north
        struct.pack("!H", 100),                         # accuracy × 1e2 = 1.00 m (unsigned short)
        now,                                            # last_update timestamp (int)
    ]
    return umsgpack.packb({SID_TIME: now, SID_LOCATION: location})


def make_icon_appearance():
    """
    Build a FIELD_ICON_APPEARANCE value: [icon_name, fg_bytes, bg_bytes].
    Uses a map-marker icon with white foreground on a blue background.
    """
    fg = struct.pack("!BBB", 255, 255, 255)  # white
    bg = struct.pack("!BBB",   0, 100, 200)  # blue
    return ["map-marker", fg, bg]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Broadcast a fixed GPS coordinate as Reticulum/LXMF telemetry "
            "compatible with Sideband and meshmap.reticulum.network"
        )
    )
    parser.add_argument(
        "--lat", type=float, required=True,
        help="Latitude in decimal degrees (e.g. 37.7749)"
    )
    parser.add_argument(
        "--lon", type=float, required=True,
        help="Longitude in decimal degrees (e.g. -122.4194)"
    )
    parser.add_argument(
        "--alt", type=float, default=0.0,
        help="Altitude in metres above sea level (default: 0)"
    )
    parser.add_argument(
        "--name", type=str, default="",
        help="Display name shown on meshmap (e.g. 'MyPi')"
    )
    parser.add_argument(
        "--collector", type=str, default=None,
        help=(
            "LXMF destination hash of the telemetry collector in hex "
            "(e.g. from meshmap.reticulum.network). "
            "Without this the beacon only announces itself."
        )
    )
    parser.add_argument(
        "--interval", type=int, default=300,
        help="Seconds between telemetry transmissions (default: 300)"
    )
    args = parser.parse_args()

    rns_configdir = os.path.expanduser("~/.reticulum")
    identity_path = os.path.join(rns_configdir, IDENTITY_FILENAME)
    lxmf_storage  = os.path.join(rns_configdir, LXMF_STORAGE_DIR)

    RNS.log(
        f"Starting telemetry beacon '{args.name}' at "
        f"({args.lat:.6f}, {args.lon:.6f}, alt={args.alt:.1f} m), "
        f"interval={args.interval}s"
    )

    # Connect to the existing rnsd shared instance (or run standalone).
    reticulum = RNS.Reticulum(configdir=rns_configdir)

    # Load or create a persistent identity for this beacon.
    if os.path.isfile(identity_path):
        identity = RNS.Identity.from_file(identity_path)
        RNS.log(f"Loaded beacon identity from {identity_path}")
    else:
        identity = RNS.Identity()
        identity.to_file(identity_path)
        RNS.log(f"Created new beacon identity, saved to {identity_path}")

    # Initialise LXMF router.
    os.makedirs(lxmf_storage, exist_ok=True)
    router = LXMF.LXMRouter(
        identity=identity,
        storagepath=lxmf_storage,
        autopeer=False,
    )

    # Register our LXMF delivery address.
    display_name = args.name if args.name else None
    lxmf_dest = router.register_delivery_identity(
        identity,
        display_name=display_name,
    )
    RNS.log(f"Beacon LXMF address: {RNS.prettyhex(lxmf_dest.hash)}")

    # Validate and store collector hash.
    collector_hash = None
    if args.collector:
        try:
            h = args.collector.replace(":", "").replace(" ", "").lower()
            collector_hash = bytes.fromhex(h)
            expected_len = RNS.Reticulum.TRUNCATED_HASHLENGTH // 8
            if len(collector_hash) != expected_len:
                raise ValueError(
                    f"Expected {expected_len}-byte hash "
                    f"({expected_len * 2} hex chars), "
                    f"got {len(collector_hash)}"
                )
            RNS.log(f"Collector: {RNS.prettyhex(collector_hash)}")
        except Exception as exc:
            RNS.log(f"Invalid --collector address: {exc}", RNS.LOG_ERROR)
            sys.exit(1)

    def send_telemetry():
        packed   = pack_telemetry(args.lat, args.lon, args.alt)
        fields   = {
            LXMF.FIELD_TELEMETRY:        packed,
            LXMF.FIELD_ICON_APPEARANCE:  make_icon_appearance(),
        }

        # Always re-announce so the network sees us as alive.
        try:
            router.announce(lxmf_dest.hash)
        except Exception as exc:
            RNS.log(f"Announce failed: {exc}", RNS.LOG_WARNING)

        if collector_hash is None:
            RNS.log("No collector configured; announced only.")
            return

        # Look up the collector identity from RNS path table.
        dest_identity = RNS.Identity.recall(collector_hash)
        if dest_identity is None:
            RNS.log(
                f"Collector {RNS.prettyhex(collector_hash)} identity not yet "
                "known — requesting path. Will retry next interval.",
                RNS.LOG_WARNING,
            )
            RNS.Transport.request_path(collector_hash)
            return

        dest = RNS.Destination(
            dest_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        lxm = LXMF.LXMessage(
            dest,
            lxmf_dest,
            "",
            desired_method=LXMF.LXMessage.DIRECT,
            fields=fields,
        )

        # Fall back to propagation node if direct delivery fails.
        if router.get_outbound_propagation_node() is not None:
            lxm.try_propagation_on_fail = True

        router.handle_outbound(lxm)
        RNS.log(
            f"Telemetry queued → collector {RNS.prettyhex(collector_hash)}"
        )

    # Graceful shutdown on SIGINT / SIGTERM.
    stop_event = threading.Event()

    def _handle_signal(sig, frame):
        RNS.log("Shutting down telemetry beacon…")
        stop_event.set()

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Give the Reticulum network a moment to discover paths, then loop.
    RNS.log("Waiting 10 s for network paths before first send…")
    stop_event.wait(10)

    while not stop_event.is_set():
        send_telemetry()
        stop_event.wait(args.interval)

    RNS.log("Telemetry beacon stopped.")


if __name__ == "__main__":
    main()
