#!/usr/bin/env python3
"""
Resource Tracker - Monitor and track system resources over time.
Logs CPU, memory, disk, and network usage to a SQLite database.
"""

import argparse
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Error: psutil library required. Install with: pip install psutil")
    sys.exit(1)


DB_PATH = Path(__file__).parent / "resource_data.db"
LOG_PATH = Path(__file__).parent / "resource_tracker.log"


def setup_logging(verbose=False):
    """Configure logging with file and console handlers."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    logger.handlers.clear()

    file_handler = logging.FileHandler(LOG_PATH)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def init_database():
    """Initialize SQLite database with required tables."""
    logger = logging.getLogger(__name__)
    logger.debug(f"Initializing database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resource_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cpu_percent REAL,
            memory_used REAL,
            memory_total REAL,
            memory_percent REAL,
            disk_used REAL,
            disk_total REAL,
            disk_percent REAL,
            bytes_sent INTEGER,
            bytes_recv INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS process_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            pid INTEGER,
            name TEXT,
            cpu_percent REAL,
            memory_percent REAL,
            memory_info TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def get_system_resources():
    """Collect current system resource metrics."""
    logger = logging.getLogger(__name__)
    logger.debug("Collecting system resource metrics")

    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net_io = psutil.net_io_counters()

    data = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': cpu_percent,
        'memory_used': memory.used / (1024 ** 3),
        'memory_total': memory.total / (1024 ** 3),
        'memory_percent': memory.percent,
        'disk_used': disk.used / (1024 ** 3),
        'disk_total': disk.total / (1024 ** 3),
        'disk_percent': disk.percent,
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv
    }

    logger.debug(f"CPU: {cpu_percent}%, Memory: {data['memory_percent']}%, Disk: {data['disk_percent']}%")
    return data


def get_top_processes(limit=5):
    """Get top processes by CPU usage."""
    logger = logging.getLogger(__name__)
    logger.debug(f"Collecting top {limit} processes by CPU usage")

    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            if info['cpu_percent'] is not None:
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cpu_percent': info['cpu_percent'],
                    'memory_percent': info['memory_percent'] or 0
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"Skipping process: {e}")
            continue

    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
    result = processes[:limit]
    logger.debug(f"Found {len(result)} top processes")
    return result


def save_snapshot(resources):
    """Save resource snapshot to database."""
    logger = logging.getLogger(__name__)
    logger.debug("Saving resource snapshot to database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO resource_snapshots
        (timestamp, cpu_percent, memory_used, memory_total, memory_percent,
         disk_used, disk_total, disk_percent, bytes_sent, bytes_recv)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        resources['timestamp'],
        resources['cpu_percent'],
        resources['memory_used'],
        resources['memory_total'],
        resources['memory_percent'],
        resources['disk_used'],
        resources['disk_total'],
        resources['disk_percent'],
        resources['bytes_sent'],
        resources['bytes_recv']
    ))

    conn.commit()
    conn.close()
    logger.info(f"Snapshot saved: CPU={resources['cpu_percent']}%, Mem={resources['memory_percent']}%")


def save_process_snapshot(timestamp, processes):
    """Save process snapshots to database."""
    logger = logging.getLogger(__name__)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for proc in processes:
        cursor.execute("""
            INSERT INTO process_snapshots
            (timestamp, pid, name, cpu_percent, memory_percent, memory_info)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            proc['pid'],
            proc['name'],
            proc['cpu_percent'],
            proc['memory_percent'],
            f"{proc['memory_percent']:.2f}%"
        ))

    conn.commit()
    conn.close()
    logger.debug(f"Saved {len(processes)} process snapshots")


def display_snapshot(resources, processes=None):
    """Display current resource snapshot in terminal."""
    print("\n" + "=" * 50)
    print(f"Resource Snapshot - {resources['timestamp']}")
    print("=" * 50)

    print(f"\nCPU Usage: {resources['cpu_percent']:.1f}%")

    print(f"\nMemory:")
    print(f"  Used: {resources['memory_used']:.2f} GB / {resources['memory_total']:.2f} GB")
    print(f"  Usage: {resources['memory_percent']:.1f}%")

    print(f"\nDisk (/):")
    print(f"  Used: {resources['disk_used']:.2f} GB / {resources['disk_total']:.2f} GB")
    print(f"  Usage: {resources['disk_percent']:.1f}%")

    print(f"\nNetwork:")
    print(f"  Sent: {resources['bytes_sent'] / (1024 ** 2):.2f} MB")
    print(f"  Received: {resources['bytes_recv'] / (1024 ** 2):.2f} MB")

    if processes:
        print(f"\nTop Processes by CPU:")
        for i, proc in enumerate(processes, 1):
            print(f"  {i}. {proc['name']} (PID: {proc['pid']}) - CPU: {proc['cpu_percent']:.1f}%")

    print("=" * 50 + "\n")


def query_history(hours=1, limit=20):
    """Query and display historical data."""
    logger = logging.getLogger(__name__)
    logger.debug(f"Querying history, limit={limit}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, cpu_percent, memory_percent, disk_percent
        FROM resource_snapshots
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        logger.info("No historical data found")
        print("No historical data found. Run with --monitor to collect data.")
        return

    logger.debug(f"Found {len(rows)} historical records")
    print(f"\nLast {len(rows)} snapshots:")
    print("-" * 70)
    print(f"{'Timestamp':<25} {'CPU%':<8} {'Mem%':<8} {'Disk%':<8}")
    print("-" * 70)

    for row in rows:
        ts, cpu, mem, disk = row
        ts_short = ts[11:19] if len(ts) > 19 else ts
        print(f"{ts_short:<25} {cpu:<8.1f} {mem:<8.1f} {disk:<8.1f}")

    print("-" * 70)


def calculate_averages():
    """Calculate and display average resource usage."""
    logger = logging.getLogger(__name__)
    logger.debug("Calculating resource usage averages")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            AVG(cpu_percent),
            AVG(memory_percent),
            AVG(disk_percent),
            COUNT(*),
            MIN(timestamp),
            MAX(timestamp)
        FROM resource_snapshots
    """)

    row = cursor.fetchone()
    conn.close()

    if row[3] == 0:
        logger.info("No data available for statistics")
        print("No data available for statistics.")
        return

    avg_cpu, avg_mem, avg_disk, count, first_ts, last_ts = row

    logger.info(f"Calculated averages from {count} snapshots")
    print("\nResource Usage Statistics")
    print("=" * 40)
    print(f"Total snapshots: {count}")
    print(f"Time range: {first_ts[:19]} to {last_ts[:19]}")
    print(f"\nAverages:")
    print(f"  CPU: {avg_cpu:.1f}%")
    print(f"  Memory: {avg_mem:.1f}%")
    print(f"  Disk: {avg_disk:.1f}%")
    print("=" * 40)


def monitor_continuous(interval=5, duration=None):
    """Monitor resources continuously."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting continuous monitoring (interval={interval}s, duration={duration}s)")

    print(f"Starting resource monitoring (interval: {interval}s)")
    if duration:
        print(f"Duration: {duration} seconds")
    print("Press Ctrl+C to stop\n")

    start_time = time.time()
    snapshot_count = 0

    try:
        while True:
            if duration and (time.time() - start_time) > duration:
                logger.info(f"Monitoring completed after {duration} seconds")
                break

            resources = get_system_resources()
            processes = get_top_processes(3)

            save_snapshot(resources)
            save_process_snapshot(resources['timestamp'], processes)

            display_snapshot(resources, processes)

            snapshot_count += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info(f"Monitoring stopped by user. {snapshot_count} snapshots collected.")
        print(f"\nMonitoring stopped. {snapshot_count} snapshots collected.")

    calculate_averages()


def export_to_csv(output_file="resource_export.csv"):
    """Export historical data to CSV."""
    logger = logging.getLogger(__name__)
    logger.info(f"Exporting data to {output_file}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM resource_snapshots ORDER BY timestamp")
    rows = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]

    conn.close()

    if not rows:
        logger.warning("No data to export")
        print("No data to export.")
        return

    with open(output_file, 'w') as f:
        f.write(','.join(columns) + '\n')
        for row in rows:
            f.write(','.join(str(v) for v in row) + '\n')

    logger.info(f"Exported {len(rows)} records to {output_file}")
    print(f"Exported {len(rows)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Resource Tracker - Monitor system resources over time"
    )
    parser.add_argument(
        '--monitor', '-m',
        action='store_true',
        help="Start continuous monitoring"
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help="Monitoring interval in seconds (default: 5)"
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        help="Monitoring duration in seconds (default: unlimited)"
    )
    parser.add_argument(
        '--snapshot', '-s',
        action='store_true',
        help="Take a single resource snapshot"
    )
    parser.add_argument(
        '--history',
        action='store_true',
        help="Show historical data"
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help="Show usage statistics"
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help="Export data to CSV"
    )
    parser.add_argument(
        '--output', '-o',
        default="resource_export.csv",
        help="Output file for CSV export"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Enable verbose logging output"
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    logger.info("Resource Tracker started")

    init_database()

    if args.monitor:
        monitor_continuous(args.interval, args.duration)
    elif args.snapshot:
        resources = get_system_resources()
        processes = get_top_processes(5)
        save_snapshot(resources)
        save_process_snapshot(resources['timestamp'], processes)
        display_snapshot(resources, processes)
        logger.info("Single snapshot taken and saved")
        print("Snapshot saved to database.")
    elif args.history:
        query_history()
    elif args.stats:
        calculate_averages()
    elif args.export:
        export_to_csv(args.output)
    else:
        resources = get_system_resources()
        display_snapshot(resources)
        logger.debug("Displayed current resource snapshot")
        print("Use --help for available options")


if __name__ == "__main__":
    main()
