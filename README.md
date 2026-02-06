# Splunk Search Automation via REST API
This project automates the execution of multiple Splunk searches using the Splunk REST API, tracks their progress in real time, and exports results to CSV files. It is designed to be generic, reusable, and easily customizable for any Splunk environment or reporting use case.
The script reads SPL queries from a CSV file, runs them concurrently, monitors execution status, and saves results in structured output files.

Features
* Execute multiple Splunk searches automatically
* Supports concurrent search execution
* Real-time progress tracking (status, runtime, event count)
* Flexible time-range handling (no fixed weekly/monthly logic)
* CSV-based query input for easy customization
* Results exported to CSV for further analysis
* GitHub-safe (no hard-coded credentials)

## Requirements

- Python 3.9+
- Splunk account with REST API access

Install dependencies:
```bash
pip install requests pandas urllib3
```

## Query CSV Format

Searches are defined in a CSV file.  
Users can modify this file to suit their own use cases.

### Example `queries.csv`

```csv
title,host,app,query,output
Failed Logins,splunk.company.com,search,index=auth action=failure,Reports/failed_logins.csv
Blocked IPs,splunk.company.com,search,index=firewall action=blocked,Reports/blocked_ips.csv
