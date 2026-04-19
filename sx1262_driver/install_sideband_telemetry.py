"""
Console script: sx1262-configure-sideband

Configures Sideband's telemetry settings with a fixed location so that this
node appears on the Reticulum mesh map (meshmap.reticulum.network).

Sideband stores its config as a msgpack binary file. This script patches that
file in-place, so Sideband must have been run at least once first to create it.

Usage:
    sx1262-configure-sideband --lat 42.3430 --lon -71.1270
    sx1262-configure-sideband --lat 42.3430 --lon -71.1270 --alt 15 --name "My Node"

After running, restart Sideband:
    sideband --daemon
"""

import argparse
import os
import sys

SIDEBAND_CONFIG_PATH = os.path.expanduser(
    "~/.config/sideband/app_storage/sideband_config"
)


def main():
    parser = argparse.ArgumentParser(
        description="Configure Sideband telemetry for Reticulum mesh map visibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--lat", type=float, required=True,
        help="Fixed latitude in decimal degrees (e.g. 42.3430)",
    )
    parser.add_argument(
        "--lon", type=float, required=True,
        help="Fixed longitude in decimal degrees (e.g. -71.1270)",
    )
    parser.add_argument(
        "--alt", type=float, default=0.0,
        help="Altitude in meters above sea level (default: 0.0)",
    )
    parser.add_argument(
        "--name", type=str, default=None,
        help="Display name for this node on the mesh map",
    )
    args = parser.parse_args()

    # Validate coordinate ranges
    if not (-90.0 <= args.lat <= 90.0):
        print(f"Error: latitude {args.lat} is out of range [-90, 90]")
        sys.exit(1)
    if not (-180.0 <= args.lon <= 180.0):
        print(f"Error: longitude {args.lon} is out of range [-180, 180]")
        sys.exit(1)

    # Use RNS's bundled umsgpack so we don't need an extra dependency
    try:
        import RNS.vendor.umsgpack as msgpack
    except ImportError:
        print("Error: RNS (Reticulum) is not installed.")
        print("Install with: pip install rns")
        sys.exit(1)

    if not os.path.isfile(SIDEBAND_CONFIG_PATH):
        print(f"Sideband config not found at:\n  {SIDEBAND_CONFIG_PATH}")
        print()
        print("Sideband must be run at least once before this script can patch it.")
        print("Start it with:  sideband --daemon")
        print("Wait a moment for it to initialise, then Ctrl-C and run this script.")
        sys.exit(1)

    # Read the existing msgpack config
    try:
        with open(SIDEBAND_CONFIG_PATH, "rb") as fh:
            config = msgpack.unpackb(fh.read())
    except Exception as exc:
        print(f"Error reading Sideband config: {exc}")
        sys.exit(1)

    # Patch telemetry settings
    config["telemetry_enabled"] = True
    config["telemetry_s_location"] = False        # use fixed location, not GPS
    config["telemetry_s_fixed_location"] = True
    config["telemetry_s_fixed_latlon"] = [args.lat, args.lon]
    config["telemetry_s_fixed_altitude"] = args.alt

    if args.name is not None:
        config["display_name"] = args.name

    # Write the patched config back
    try:
        with open(SIDEBAND_CONFIG_PATH, "wb") as fh:
            fh.write(msgpack.packb(config))
    except Exception as exc:
        print(f"Error writing Sideband config: {exc}")
        sys.exit(1)

    print("Sideband telemetry configured successfully.")
    print(f"  Config path : {SIDEBAND_CONFIG_PATH}")
    print(f"  Latitude    : {args.lat}")
    print(f"  Longitude   : {args.lon}")
    print(f"  Altitude    : {args.alt} m")
    if args.name:
        print(f"  Display name: {args.name}")
    print()
    print("Restart Sideband for changes to take effect:")
    print("  sideband --daemon")
