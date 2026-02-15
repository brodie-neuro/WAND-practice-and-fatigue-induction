#!/usr/bin/env python3
"""
WAND EEG Test Utility

Scans common parallel port addresses to find a working USB-to-parallel adapter,
sends test triggers, and saves the detected address to params.json.

Usage:
    wand-eeg-test           # Run from command line after pip install
    python -m wand_nback.eeg_test   # Run directly

Author: Brodie E. Mangan
License: MIT
"""

import json
import os
import sys
import time

# Common parallel port I/O addresses to scan
# LPT = Line Print Terminal (legacy parallel port naming)
COMMON_PORT_ADDRESSES = [
    # Standard motherboard/PCI parallel ports
    "0x378",  # LPT1 - most common standard address
    "0x278",  # LPT2 - secondary standard address
    "0x3BC",  # LPT3 - older standard, sometimes LPT1 on some systems
    # Common USB-to-parallel adapter addresses (varies by manufacturer)
    "0xD010",  # Common USB adapter (Delock, generic)
    "0xD050",  # Common USB adapter variant
    "0xE010",  # Common USB adapter (StarTech, generic)
    "0xE050",  # Common USB adapter variant
    "0xD000",  # Common USB adapter
    "0xE000",  # Common USB adapter
    "0xDF00",  # Some USB adapters
    "0xEF00",  # Some USB adapters
    # PCI/PCIe parallel port card addresses
    "0x3FF8",  # Common PCIe parallel port card
    "0xEC00",  # Some PCIe cards
    "0xDC00",  # Some PCIe cards
    # Extended range for less common adapters
    "0xD008",
    "0xE008",
    "0xD100",
    "0xE100",
]


def get_config_path():
    """Get path to params.json config file."""
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config", "params.json")


def load_config():
    """Load current params.json configuration."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save updated configuration to params.json."""
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"[EEG] Configuration saved to: {config_path}")


# =============================================================================
# TRIGGERBOX DETECTION (Brain Products)
# =============================================================================


def scan_triggerbox():
    """
    Scan COM ports for Brain Products TriggerBox.

    Returns:
        (port_name, serial_connection) if found, (None, None) if not found
    """
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        print("[EEG] pyserial not installed - TriggerBox detection unavailable")
        return None, None

    print("\n[EEG] Scanning for Brain Products TriggerBox...")

    ports = list(serial.tools.list_ports.comports())

    if not ports:
        print("[EEG] No COM ports found")
        return None, None

    for port_info in ports:
        port_name = port_info.device
        description = port_info.description.lower()

        print(
            f"[EEG] Checking {port_name}: {port_info.description}... ",
            end="",
            flush=True,
        )

        # Check if this looks like a TriggerBox
        if "triggerbox" in description or "brain products" in description:
            try:
                # Try to open the port
                ser = serial.Serial(port=port_name, baudrate=115200, timeout=1)
                print(f"SUCCESS - TriggerBox found!")
                return port_name, ser
            except Exception as e:
                print(f"FAILED to open: {e}")
        else:
            print("NOT TRIGGERBOX")

    return None, None


def send_triggerbox_trigger(serial_conn, trigger_code=1, duration=0.005):
    """Send a trigger via TriggerBox serial connection."""
    try:
        # TriggerBox protocol: send byte directly
        serial_conn.write(bytes([trigger_code]))
        time.sleep(duration)
        serial_conn.write(bytes([0]))  # Reset
        return True
    except Exception as e:
        print(f"[EEG] ERROR: Failed to send TriggerBox trigger: {e}")
        return False


# =============================================================================
# PARALLEL PORT DETECTION
# =============================================================================


def try_port(address_str):
    """
    Attempt to initialise parallel port at given address.

    Returns:
        port object if successful, None if failed
    """
    try:
        from psychopy import parallel

        # Convert hex string to int
        if isinstance(address_str, str):
            port_addr = int(address_str, 16)
        else:
            port_addr = address_str

        port = parallel.ParallelPort(address=port_addr)
        return port
    except Exception as e:
        return None


def send_test_trigger(port, trigger_code=1, duration=0.005):
    """Send a test trigger pulse and return success status."""
    try:
        port.setData(trigger_code)
        time.sleep(duration)
        port.setData(0)
        return True
    except Exception as e:
        print(f"[EEG] ERROR: Failed to send trigger: {e}")
        return False


def measure_timing_jitter(port, num_triggers=100, target_interval=0.1):
    """
    Measure timing jitter by sending triggers at fixed intervals.

    This measures the SOFTWARE-SIDE timing precision. The actual jitter
    at the EEG amplifier may be higher due to USB buffering.

    Parameters
    ----------
    port : parallel.ParallelPort
        Initialised parallel port object
    num_triggers : int
        Number of triggers to send (default 100)
    target_interval : float
        Target interval between triggers in seconds (default 0.1s = 100ms)

    Returns
    -------
    dict
        Timing statistics: mean_interval, sd, min, max, max_deviation
    """
    print(f"\n[EEG] TIMING JITTER MEASUREMENT")
    print(
        f"[EEG] Sending {num_triggers} triggers at {target_interval*1000:.0f}ms intervals..."
    )
    print(f"[EEG] This measures software-side timing precision.\n")

    timestamps = []

    for i in range(num_triggers):
        t_start = time.perf_counter()

        # Send trigger
        port.setData(1)
        time.sleep(0.005)  # 5ms pulse
        port.setData(0)

        timestamps.append(t_start)

        # Progress indicator every 25 triggers
        if (i + 1) % 25 == 0:
            print(f"[EEG] Progress: {i+1}/{num_triggers} triggers sent")

        # Wait for remainder of interval
        elapsed = time.perf_counter() - t_start
        if elapsed < target_interval:
            time.sleep(target_interval - elapsed)

    # Calculate intervals between consecutive triggers
    intervals = []
    for i in range(1, len(timestamps)):
        intervals.append(timestamps[i] - timestamps[i - 1])

    # Statistics
    import statistics
    from datetime import datetime

    mean_interval = statistics.mean(intervals)
    sd_interval = statistics.stdev(intervals)
    min_interval = min(intervals)
    max_interval = max(intervals)
    max_deviation = max(abs(i - target_interval) for i in intervals)

    # Convert to milliseconds for reporting
    mean_ms = mean_interval * 1000
    sd_ms = sd_interval * 1000
    min_ms = min_interval * 1000
    max_ms = max_interval * 1000
    max_dev_ms = max_deviation * 1000

    # Determine assessment
    if max_dev_ms < 5:
        assessment = "EXCELLENT: Jitter < 5ms - suitable for all EEG analyses"
    elif max_dev_ms < 15:
        assessment = (
            "GOOD: Jitter < 15ms - suitable for ERP and most oscillatory analyses"
        )
    elif max_dev_ms < 30:
        assessment = "MODERATE: Jitter < 30ms - acceptable for ERP, may affect fine PAC estimates"
    else:
        assessment = "HIGH: Jitter >= 30ms - consider using a PCI parallel port card"

    print(f"\n" + "=" * 60)
    print("TIMING JITTER RESULTS")
    print("=" * 60)
    print(f"\nTarget interval:     {target_interval*1000:.1f} ms")
    print(f"Mean interval:       {mean_ms:.2f} ms")
    print(f"Standard deviation:  {sd_ms:.3f} ms")
    print(f"Min interval:        {min_ms:.2f} ms")
    print(f"Max interval:        {max_ms:.2f} ms")
    print(f"Max deviation:       {max_dev_ms:.3f} ms")
    print(f"\n--- FOR METHODS SECTION ---")
    print(f"Trigger timing precision: M = {mean_ms:.2f} ms, SD = {sd_ms:.2f} ms")
    print(f"Maximum timing deviation: {max_dev_ms:.2f} ms")
    print(f"\n{assessment}")
    print("=" * 60)

    # Save report to file
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    data_dir = os.path.join(os.path.dirname(base_dir), "data")
    os.makedirs(data_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(data_dir, f"eeg_jitter_report_{timestamp}.txt")

    config = load_config()
    port_address = config.get("eeg", {}).get("port_address", "unknown")

    report_content = f"""WAND EEG Trigger Jitter Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

CONFIGURATION
-------------
Port Address: {port_address}
Number of Test Triggers: {num_triggers}
Target Interval: {target_interval*1000:.1f} ms

TIMING STATISTICS
-----------------
Mean Interval:       {mean_ms:.3f} ms
Standard Deviation:  {sd_ms:.3f} ms
Min Interval:        {min_ms:.3f} ms
Max Interval:        {max_ms:.3f} ms
Max Deviation:       {max_dev_ms:.3f} ms

ASSESSMENT
----------
{assessment}

FOR METHODS SECTION
-------------------
Trigger timing precision: M = {mean_ms:.2f} ms, SD = {sd_ms:.2f} ms
Maximum timing deviation: {max_dev_ms:.2f} ms
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n[EEG] Report saved to: {report_path}")

    return {
        "mean_ms": mean_ms,
        "sd_ms": sd_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "max_deviation_ms": max_dev_ms,
        "n_triggers": num_triggers,
        "report_path": report_path,
    }


def scan_ports():
    """
    Scan common port addresses to find a working parallel port.

    Returns:
        (address_str, port) if found, (None, None) if no port found
    """
    print("\n" + "=" * 60)
    print("WAND EEG TEST UTILITY")
    print("=" * 60)
    print("\nScanning for parallel port...\n")

    for address in COMMON_PORT_ADDRESSES:
        print(f"[EEG] Trying {address}... ", end="", flush=True)

        port = try_port(address)

        if port is not None:
            # Try sending a test trigger
            if send_test_trigger(port, trigger_code=255):
                print(f"SUCCESS ✓")
                print(f"[EEG] Parallel port found at {address}")
                return address, port
            else:
                print(f"INIT OK, TRIGGER FAILED")
        else:
            print(f"NOT FOUND")

    return None, None


def run_eeg_test():
    """Main EEG test routine - auto-detects TriggerBox or parallel port."""

    print("\n" + "=" * 60)
    print("WAND EEG TEST UTILITY")
    print("=" * 60)
    print("\nAuto-detecting trigger device...")
    print("Checking for: TriggerBox (USB serial) and Parallel Port")

    # Load current config
    config = load_config()
    current_mode = config.get("eeg", {}).get("trigger_mode", "auto")
    current_address = config.get("eeg", {}).get("port_address", "0x378")
    current_triggerbox = config.get("eeg", {}).get("triggerbox_port", None)
    eeg_enabled = config.get("eeg", {}).get("enabled", False)

    print(f"\nCurrent configuration:")
    print(f"  - EEG enabled: {eeg_enabled}")
    print(f"  - Trigger mode: {current_mode}")
    if current_triggerbox:
        print(f"  - TriggerBox port: {current_triggerbox}")
    print(f"  - Parallel port address: {current_address}")

    found_device = False
    trigger_mode = None
    device_info = None

    # =================================================================
    # STEP 1: Try TriggerBox (preferred - better timing)
    # =================================================================
    triggerbox_port, serial_conn = scan_triggerbox()

    if triggerbox_port is not None:
        print(f"\n[EEG] TriggerBox detected on {triggerbox_port}")
        print("[EEG] Sending 5 test triggers (code 1) at 1 second intervals...\n")

        for i in range(5):
            time.sleep(1)
            if send_triggerbox_trigger(serial_conn, trigger_code=1):
                print(
                    f"[EEG] Trigger {i+1}/5 sent (code 1) via TriggerBox {triggerbox_port} ✓"
                )
            else:
                print(f"[EEG] Trigger {i+1}/5 FAILED")

        # Update config
        if "eeg" not in config:
            config["eeg"] = {}
        config["eeg"]["enabled"] = True
        config["eeg"]["trigger_mode"] = "triggerbox"
        config["eeg"]["triggerbox_port"] = triggerbox_port

        save_config(config)

        print("\n" + "=" * 60)
        print("EEG TEST COMPLETE - TriggerBox configured")
        print("=" * 60)
        print(f"\nTrigger mode: TriggerBox")
        print(f"Port: {triggerbox_port}")
        print("Configuration saved to params.json")
        print("\nYou can now run 'wand-launcher' or 'wand-quicktest'")
        print("Triggers will be sent automatically during stimulus presentation.\n")

        serial_conn.close()
        return True

    # =================================================================
    # STEP 2: Try configured parallel port address
    # =================================================================
    print(f"\n[EEG] No TriggerBox found. Trying parallel port...")
    print(f"[EEG] Trying configured address {current_address}... ", end="", flush=True)

    port = try_port(current_address)

    if port is not None and send_test_trigger(port, trigger_code=255):
        print(f"SUCCESS ✓")
        print(f"\n[EEG] Configured port {current_address} is working!")
        print("[EEG] Sending 5 test triggers (code 1) at 1 second intervals...\n")

        for i in range(5):
            time.sleep(1)
            if send_test_trigger(port, trigger_code=1):
                print(f"[EEG] Trigger {i+1}/5 sent (code 1) via {current_address} ✓")
            else:
                print(f"[EEG] Trigger {i+1}/5 FAILED")

        # Update config
        if "eeg" not in config:
            config["eeg"] = {}
        config["eeg"]["enabled"] = True
        config["eeg"]["trigger_mode"] = "parallel"

        save_config(config)

        print("\n" + "=" * 60)
        print("EEG TEST COMPLETE - Parallel port configured")
        print("=" * 60)
        print(f"\nTrigger mode: Parallel Port")
        print(f"Address: {current_address}")
        print("Configuration saved to params.json")
        return True
    else:
        print(f"NOT FOUND or FAILED")

    # =================================================================
    # STEP 3: Scan all common parallel port addresses
    # =================================================================
    print("\n[EEG] Configured address didn't work. Scanning alternatives...")
    found_address, port = scan_ports()

    if found_address is None:
        print("\n" + "=" * 60)
        print("NO TRIGGER DEVICE FOUND")
        print("=" * 60)
        print("\nChecked for:")
        print("  - Brain Products TriggerBox (USB serial)")
        print("  - Parallel port (18 common addresses)")
        print("\nPossible causes:")
        print("  1. No trigger hardware connected")
        print("  2. Drivers not installed")
        print("  3. Port address not in common list")
        print("\nTo find your parallel port address manually:")
        print("  1. Open Device Manager (Win + X)")
        print("  2. Expand 'Ports (COM & LPT)'")
        print("  3. Right-click adapter -> Properties -> Resources")
        print("  4. Note the I/O Range value (e.g., E010-E017)")

        # =================================================================
        # STEP 4: Ask user for manual address input
        # =================================================================
        print("\n" + "-" * 60)
        try:
            manual_address = input(
                "Enter port address manually (e.g., 0xE010), or press Enter to skip: "
            ).strip()
        except EOFError:
            # Non-interactive mode (e.g., in CI)
            manual_address = ""

        if not manual_address:
            print("[EEG] No address entered. Exiting.")
            return False

        # Validate and test the manual address
        if not manual_address.startswith("0x"):
            manual_address = "0x" + manual_address

        print(f"\n[EEG] Trying manual address {manual_address}... ", end="", flush=True)
        port = try_port(manual_address)

        if port is not None and send_test_trigger(port, trigger_code=255):
            print(f"SUCCESS ✓")
            print(f"\n[EEG] Port {manual_address} is working!")
            print("[EEG] Sending 5 test triggers (code 1) at 1 second intervals...\n")

            for i in range(5):
                time.sleep(1)
                if send_test_trigger(port, trigger_code=1):
                    print(f"[EEG] Trigger {i+1}/5 sent (code 1) via {manual_address} ✓")
                else:
                    print(f"[EEG] Trigger {i+1}/5 FAILED")

            # Save to config
            if "eeg" not in config:
                config["eeg"] = {}
            config["eeg"]["port_address"] = manual_address
            config["eeg"]["enabled"] = True
            config["eeg"]["trigger_mode"] = "parallel"

            save_config(config)

            print("\n" + "=" * 60)
            print("EEG TEST COMPLETE - Manual address configured")
            print("=" * 60)
            print(f"\nTrigger mode: Parallel Port")
            print(f"Address: {manual_address}")
            print("Configuration saved to params.json")
            print("\nYou can now run 'wand-launcher' or 'wand-quicktest'")
            print("Triggers will be sent automatically during stimulus presentation.\n")
            return True
        else:
            print(f"FAILED")
            print(f"\n[EEG] Address {manual_address} did not work.")
            print("[EEG] Please verify the address in Device Manager and try again.")
            return False

    # Port found - update config
    print(f"\n[EEG] Parallel port found at {found_address}")
    print("[EEG] Sending 5 test triggers (code 1) at 1 second intervals...\n")

    for i in range(5):
        time.sleep(1)
        if send_test_trigger(port, trigger_code=1):
            print(f"[EEG] Trigger {i+1}/5 sent (code 1) via {found_address} ✓")
        else:
            print(f"[EEG] Trigger {i+1}/5 FAILED")

    if "eeg" not in config:
        config["eeg"] = {}
    config["eeg"]["port_address"] = found_address
    config["eeg"]["enabled"] = True
    config["eeg"]["trigger_mode"] = "parallel"

    save_config(config)

    print("\n" + "=" * 60)
    print("EEG TEST COMPLETE")
    print("=" * 60)
    print(f"\nTrigger mode: Parallel Port")
    print(f"Address: {found_address}")
    print("Configuration saved to params.json")
    print("\nYou can now run 'wand-launcher' or 'wand-quicktest'")
    print("Triggers will be sent automatically during stimulus presentation.\n")

    return True


def main():
    """Entry point for wand-eeg-test command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WAND EEG Test Utility - Scan for parallel port and verify triggers"
    )
    parser.add_argument(
        "--jitter",
        action="store_true",
        help="Run timing jitter measurement (100 triggers) after port detection",
    )
    args = parser.parse_args()

    try:
        success = run_eeg_test()

        if success and args.jitter:
            # Get the port again for jitter test
            config = load_config()
            address = config.get("eeg", {}).get("port_address", "0x378")
            port = try_port(address)
            if port:
                measure_timing_jitter(port)

        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[EEG] Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[EEG] ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
