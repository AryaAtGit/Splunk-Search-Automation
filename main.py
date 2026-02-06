import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import os
import csv
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

# =========================
# Configuration (User Editable)
# =========================

SPLUNK_USERNAME = os.getenv("SPLUNK_USERNAME")
SPLUNK_PASSWORD = os.getenv("SPLUNK_PASSWORD")

QUERY_CSV = "queries.csv"
PROGRESS_FILE = "Reports/progress.csv"
MAX_CONCURRENT_SEARCHES = 5
REFRESH_INTERVAL = 5


# =========================
# Utility Functions
# =========================

def time_range(start_offset_days=30, end_offset_days=0, end_hour=0, end_minute=0):
    """
    Generate ISO time range for Splunk searches.

    If date-time filters are required, use this function
    and adjust offsets as needed.
    """

    end_time = datetime.today().replace(
        hour=end_hour,
        minute=end_minute,
        second=0,
        microsecond=0
    ) - timedelta(days=end_offset_days)

    start_time = end_time - timedelta(days=start_offset_days)

    return start_time.isoformat(), end_time.isoformat()


def create_progress_df():
    return pd.DataFrame(
        columns=["Title", "Status", "Progress (%)", "Events", "Runtime (s)"]
    )


def render_progress(df):
    os.system("cls" if os.name == "nt" else "clear")
    print("Splunk Search Progress\n")
    print(df.fillna("").to_string(index=False))


def export_progress(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def write_csv(data, file_path):
    if not data:
        return

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    fieldnames = set()
    for row in data:
        fieldnames.update(row.keys())

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
        writer.writeheader()
        writer.writerows(data)


# =========================
# Splunk Search Functions
# =========================

def start_search(search, progress_df):
    app = search.get("app", "search")
    url = f"https://{search['host']}:8089/servicesNS/{SPLUNK_USERNAME}/{app}/search/jobs"

    query = search["query"].strip()
    query = query if query.startswith("|") else f"search {query}"

    r = requests.post(
        url,
        auth=(SPLUNK_USERNAME, SPLUNK_PASSWORD),
        data={
            "search": query,
            "earliest_time": search.get("earliest"),
            "latest_time": search.get("latest")
        },
        params={"output_mode": "json"},
        verify=False
    )

    if r.status_code != 201:
        progress_df.loc[len(progress_df)] = [
            search["title"], "FAILED", 0, 0, 0
        ]
        return None

    search["sid"] = r.json()["sid"]
    search["status"] = "CREATED"

    progress_df.loc[len(progress_df)] = [
        search["title"], "CREATED", 0, 0, 0
    ]

    return search


def update_progress(search, progress_df):
    app = search.get("app", "search")
    url = f"https://{search['host']}:8089/servicesNS/{SPLUNK_USERNAME}/{app}/search/jobs/{search['sid']}"

    r = requests.get(
        url,
        auth=(SPLUNK_USERNAME, SPLUNK_PASSWORD),
        params={"output_mode": "json"},
        verify=False
    )

    content = r.json()["entry"][0]["content"]

    progress_df.loc[progress_df["Title"] == search["title"], :] = [
        search["title"],
        content.get("dispatchState"),
        round(content.get("doneProgress", 0) * 100, 2),
        content.get("eventCount", 0),
        round(content.get("runDuration", 0), 1)
    ]

    search["status"] = "DONE" if content.get("isDone") else content.get("dispatchState")


def fetch_results(search):
    app = search.get("app", "search")
    url = f"https://{search['host']}:8089/servicesNS/{SPLUNK_USERNAME}/{app}/search/jobs/{search['sid']}/results"

    r = requests.get(
        url,
        auth=(SPLUNK_USERNAME, SPLUNK_PASSWORD),
        params={"output_mode": "json", "count": 0},
        verify=False
    )

    if r.status_code == 200 and r.text.strip():
        write_csv(r.json()["results"], search["output"])


# =========================
# Main Processor
# =========================

def process_queries():
    progress_df = create_progress_df()
    earliest, latest = time_range()

    searches = []

    with open(QUERY_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("query"):
                continue

            searches.append({
                "title": row["title"].strip(),
                "host": row["host"].strip(),
                "app": row.get("app", "search").strip(),
                "query": row["query"].strip(),
                "output": row["output"].strip(),
                "earliest": earliest,
                "latest": latest
            })

    active, pending = [], searches[:]

    while pending or active:
        while len(active) < MAX_CONCURRENT_SEARCHES and pending:
            s = pending.pop(0)
            started = start_search(s, progress_df)
            if started:
                active.append(started)

        for s in active[:]:
            update_progress(s, progress_df)
            if s["status"] == "DONE":
                fetch_results(s)
                active.remove(s)
                export_progress(progress_df, PROGRESS_FILE)

        render_progress(progress_df)
        time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    process_queries()
