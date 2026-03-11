# Resource Tracker

Lightweight tool to monitor and track system resources over time. Built this because I kept forgetting what was eating my RAM at 3am during debugging sessions.

## What it does

Tracks CPU, memory, disk, and network usage. Stores everything in a SQLite database so you can look back and see patterns. Also shows top processes by CPU usage.

## Quick start

```bash
pip install -r requirements.txt
python resource_tracker.py
```

## Usage

### Single snapshot
```bash
python resource_tracker.py --snapshot
```
Takes one reading and saves it to the database.

### Continuous monitoring
```bash
python resource_tracker.py --monitor --interval 10
```
Monitors every 10 seconds. Hit Ctrl+C to stop.

Add `--duration 300` to auto-stop after 5 minutes.

### Check history
```bash
python resource_tracker.py --history
```
Shows last 20 snapshots with CPU, memory, and disk percentages.

### Statistics
```bash
python resource_tracker.py --stats
```
Shows averages across all collected data.

### Export to CSV
```bash
python resource_tracker.py --export --output my_data.csv
```
Dumps everything to CSV for plotting in your favorite tool.

### Verbose logging
```bash
python resource_tracker.py --verbose --snapshot
```
Enables detailed logging output to both console and file.

## Logging

The tracker logs all operations to `resource_tracker.log` in the same directory. Use `--verbose` to see debug-level messages in the console.

## Database

Data goes into `resource_data.db` in the same directory. Two tables:
- `resource_snapshots` - system-wide metrics
- `process_snapshots` - top processes by CPU

Query it directly if you want custom analysis.

## Why I built this

Needed something simpler than full-blown monitoring stacks. No dashboards, no alerts, just raw data I can query when things go sideways.

## Dependencies

- Python 3.7+
- psutil

That's it. No fancy stuff.
