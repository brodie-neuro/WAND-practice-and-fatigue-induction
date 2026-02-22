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
        description = port_info.description or "Unknown"

        print(f"[EEG] Checking {port_name}: {description}...", end=" ")

        # Check if this looks like a TriggerBox
        is_triggerbox = False

        # Brain Products TriggerBox identifiers
        if port_info.vid == 0x1130 or "TriggerBox" in description:
            is_triggerbox = True

        if is_triggerbox:
            try:
                ser = serial.Serial(port_name, baudrate=9600, timeout=1)
                print("TRIGGERBOX FOUND ✓")
                return port_name, ser
            except serial.SerialException as e:
                print(f"FOUND but cannot open: {e}")
                continue
        else:
            print("NOT TRIGGERBOX")

    return None, None


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

        # --- Verification Step ---
        # Write test patterns and read them back to confirm hardware presence.
        # Without this, Windows silently succeeds on empty addresses like 0x378.
        test_patterns = [170, 85]
        is_valid = True
        for pattern in test_patterns:
            port.setData(pattern)
            time.sleep(0.001)
            if port.readData() != pattern:
                is_valid = False
                break

        port.setData(0)

        if is_valid:
            return port
        else:
            return None

    except Exception as e:
        return None


def scan_parallel_ports():
    """
    Scan common parallel port addresses for a working adapter.

    Returns:
        (address_str, port_object) if found, (None, None) if not found
    """
    print("\n" + "=" * 60)
    print("WAND EEG TEST UTILITY")
    print("=" * 60)
    print("\nScanning for parallel port...\n")

    for addr in COMMON_PORT_ADDRESSES:
        print(f"[EEG] Trying {addr}...", end=" ")
        port = try_port(addr)
        if port is not None:
            print("SUCCESS ✓")
            return addr, port
        else:
            print("NOT FOUND")

    return None, None


# =============================================================================
# TRIGGER TESTING
# =============================================================================


def run_trigger_test(port, mode="parallel", num_triggers=10):
    """
    Send test triggers and measure timing.

    Parameters:
        port: parallel port object or serial connection
        mode: 'parallel' or 'triggerbox'
        num_triggers: number of test triggers to send
    """
    print(f"\nSending {num_triggers} test triggers...")
    print("-" * 40)

    timings = []

    for i in range(num_triggers):
        trigger_value = (i % 254) + 1  # Values 1-254

        t_start = time.perf_counter()

        if mode == "parallel":
            port.setData(trigger_value)
            time.sleep(0.005)
            port.setData(0)
        elif mode == "triggerbox":
            port.write(bytes([trigger_value]))
            time.sleep(0.005)
            port.write(bytes([0]))

        t_end = time.perf_counter()
        duration_ms = (t_end - t_start) * 1000
        timings.append(duration_ms)

        print(f"  Trigger {i+1:3d}: value={trigger_value:3d}  time={duration_ms:.2f}ms")
        time.sleep(0.1)  # 100ms between triggers

    # Summary statistics
    if timings:
        avg = sum(timings) / len(timings)
        min_t = min(timings)
        max_t = max(timings)

        print("\n" + "-" * 40)
        print(f"Trigger Summary ({num_triggers} triggers):")
        print(f"  Average: {avg:.2f}ms")
        print(f"  Min:     {min_t:.2f}ms")
        print(f"  Max:     {max_t:.2f}ms")
        print(f"  Range:   {max_t - min_t:.2f}ms")

    return timings


def run_jitter_test(port, mode="parallel", num_triggers=100):
    """
    Run extended jitter measurement for methods sections.

    Parameters:
        port: parallel port or serial connection
        mode: 'parallel' or 'triggerbox'
        num_triggers: number of triggers (default 100)
    """
    print(f"\n{'=' * 60}")
    print(f"TIMING JITTER MEASUREMENT ({num_triggers} triggers)")
    print(f"{'=' * 60}")

    timings = []

    for i in range(num_triggers):
        trigger_value = (i % 254) + 1

        t_start = time.perf_counter()

        if mode == "parallel":
            port.setData(trigger_value)
            time.sleep(0.005)
            port.setData(0)
        elif mode == "triggerbox":
            port.write(bytes([trigger_value]))
            time.sleep(0.005)
            port.write(bytes([0]))

        t_end = time.perf_counter()
        duration_ms = (t_end - t_start) * 1000
        timings.append(duration_ms)

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{num_triggers}")

        time.sleep(0.05)

    # Compute statistics
    import statistics

    avg = statistics.mean(timings)
    std = statistics.stdev(timings) if len(timings) > 1 else 0
    median = statistics.median(timings)
    min_t = min(timings)
    max_t = max(timings)

    print(f"\n{'=' * 60}")
    print("JITTER RESULTS")
    print(f"{'=' * 60}")
    print(f"  Triggers sent: {num_triggers}")
    print(f"  Mean:          {avg:.3f} ms")
    print(f"  Std Dev:       {std:.3f} ms")
    print(f"  Median:        {median:.3f} ms")
    print(f"  Min:           {min_t:.3f} ms")
    print(f"  Max:           {max_t:.3f} ms")
    print(f"  Range:         {max_t - min_t:.3f} ms")

    # Save report
    try:
        from datetime import datetime

        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(data_dir, f"eeg_jitter_report_{timestamp}.txt")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"WAND EEG Trigger Jitter Report\n")
            f.write(f"{'=' * 40}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {mode}\n")
            f.write(f"Triggers: {num_triggers}\n\n")
            f.write(f"Mean:    {avg:.3f} ms\n")
            f.write(f"Std Dev: {std:.3f} ms\n")
            f.write(f"Median:  {median:.3f} ms\n")
            f.write(f"Min:     {min_t:.3f} ms\n")
            f.write(f"Max:     {max_t:.3f} ms\n")
            f.write(f"Range:   {max_t - min_t:.3f} ms\n\n")
            f.write(f"Methods section text:\n")
            f.write(
                f"EEG triggers were sent via {mode} port with a mean latency of "
                f"{avg:.2f} ms (SD = {std:.2f} ms, range: {min_t:.2f}-{max_t:.2f} ms, "
                f"n = {num_triggers}).\n"
            )

        print(f"\n  Report saved to: {report_path}")
    except Exception as e:
        print(f"\n  Warning: Could not save report: {e}")

    return timings


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for wand-eeg-test CLI command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WAND EEG Trigger Test Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--jitter",
        action="store_true",
        help="Run extended jitter measurement (100 triggers)",
    )
    parser.add_argument(
        "--triggers",
        type=int,
        default=10,
        help="Number of test triggers to send (default: 10)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("WAND EEG TEST UTILITY")
    print("=" * 60)
    print("\nAuto-detecting trigger device...")
    print("Checking for: TriggerBox (USB serial) and Parallel Port\n")

    # Load current config
    config = load_config()
    eeg_config = config.get("eeg", {})
    # Prefer canonical key used by full_induction.py, but keep legacy fallback
    current_addr = eeg_config.get("port_address") or eeg_config.get(
        "parallel_port_address", "0x378"
    )
    trigger_mode = eeg_config.get("trigger_mode", "auto")
    eeg_enabled = eeg_config.get("enabled", True)

    print(f"Current configuration:")
    print(f"  - EEG enabled: {eeg_enabled}")
    print(f"  - Trigger mode: {trigger_mode}")
    print(f"  - Parallel port address: {current_addr}")

    # Step 1: Try TriggerBox first
    tb_port, tb_serial = scan_triggerbox()

    if tb_serial:
        print(f"\n{'=' * 60}")
        print(f"TRIGGERBOX DETECTED on {tb_port}")
        print(f"{'=' * 60}")

        # Update config
        eeg_config["enabled"] = True
        eeg_config["trigger_mode"] = "triggerbox"
        eeg_config["triggerbox_port"] = tb_port
        config["eeg"] = eeg_config
        save_config(config)

        # Run trigger test
        if args.jitter:
            run_jitter_test(tb_serial, mode="triggerbox", num_triggers=100)
        else:
            run_trigger_test(tb_serial, mode="triggerbox", num_triggers=args.triggers)

        tb_serial.close()
        return

    # Step 2: Try configured parallel port address first
    print(f"\n[EEG] No TriggerBox found. Trying parallel port...")
    print(f"[EEG] Trying configured address {current_addr}...", end=" ")

    port = try_port(current_addr)
    if port:
        print("SUCCESS ✓")
        found_addr = current_addr
    else:
        print("NOT FOUND or FAILED")
        print(f"\n[EEG] Configured address didn't work. Scanning alternatives...")

        # Step 3: Scan all common addresses
        found_addr, port = scan_parallel_ports()

    if port:
        print(f"\n{'=' * 60}")
        print(f"PARALLEL PORT DETECTED at {found_addr}")
        print(f"{'=' * 60}")

        # Update config
        eeg_config["enabled"] = True
        eeg_config["trigger_mode"] = "parallel"
        eeg_config["port_address"] = found_addr
        # Backward compatibility for older tooling that still reads this key
        eeg_config["parallel_port_address"] = found_addr
        config["eeg"] = eeg_config
        save_config(config)

        # Run trigger test
        if args.jitter:
            run_jitter_test(port, mode="parallel", num_triggers=100)
        else:
            run_trigger_test(port, mode="parallel", num_triggers=args.triggers)

        # Clean up
        port.setData(0)
        return

    # Step 4: Nothing found - offer manual entry
    print(f"\n{'=' * 60}")
    print("NO TRIGGER DEVICE FOUND")
    print(f"{'=' * 60}")
    print(f"\nChecked for:")
    print(f"  - Brain Products TriggerBox (USB serial)")
    print(f"  - Parallel port ({len(COMMON_PORT_ADDRESSES)} common addresses)")
    print(f"\nPossible causes:")
    print(f"  1. No trigger hardware connected")
    print(f"  2. Drivers not installed")
    print(f"  3. Port address not in common list")
    print(f"\nTo find your parallel port address manually:")
    print(f"  1. Open Device Manager (Win + X)")
    print(f"  2. Expand 'Ports (COM & LPT)'")
    print(f"  3. Right-click adapter -> Properties -> Resources")
    print(f"  4. Note the I/O Range value (e.g., E010-E017)")

    print(f"\n{'-' * 60}")
    manual_addr = input(
        "Enter port address manually (e.g., 0xE010), or press Enter to skip: "
    ).strip()

    if manual_addr:
        if not manual_addr.startswith("0x"):
            manual_addr = "0x" + manual_addr

        print(f"\n[EEG] Trying {manual_addr}...", end=" ")
        port = try_port(manual_addr)

        if port:
            print("SUCCESS ✓")
            print(f"\n{'=' * 60}")
            print(f"PARALLEL PORT DETECTED at {manual_addr}")
            print(f"{'=' * 60}")

            # Update config
            eeg_config["enabled"] = True
            eeg_config["trigger_mode"] = "parallel"
            eeg_config["port_address"] = manual_addr
            # Backward compatibility for older tooling that still reads this key
            eeg_config["parallel_port_address"] = manual_addr
            config["eeg"] = eeg_config
            save_config(config)

            # Run trigger test
            if args.jitter:
                run_jitter_test(port, mode="parallel", num_triggers=100)
            else:
                run_trigger_test(port, mode="parallel", num_triggers=args.triggers)

            port.setData(0)
        else:
            print("FAILED")
            print(f"\nCould not communicate with port at {manual_addr}")
            print("Please check the address and try again.")
    else:
        print("\nSkipped manual entry. EEG triggers will be disabled.")
        eeg_config["enabled"] = False
        config["eeg"] = eeg_config
        save_config(config)


if __name__ == "__main__":
    main()
