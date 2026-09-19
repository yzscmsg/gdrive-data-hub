# 07 — Data Hub Management Portal

## 1. Overview & Architecture

The Management Portal (`gdrive-hub-portal`) is a lightweight web application that provides complete operational observability and interactive parameter control over the data governance engine.

- **Stack**: Python FastAPI / HTTP server with a zero-dependency, self-contained Tailwind/Alpine web dashboard.
- **Port**: Defaults to `8080` (accessible over local LAN / VPN at `http://<controller-ip>:8080`).
- **Static Mirror**: Generates a static snapshot to `00_SYSTEM/index/dashboard.html` in Google Drive daily for mobile inspection when outside the LAN.

---

## 2. Core Functional Modules

### A. Governance & Policy Parameters
- **IMDb Rating Slider**: Dynamically adjust the cutoff score (e.g. from 7.8 to 8.0) to instantly expand or contract the cloud cinema footprint.
- **Schedule Controls**: Change the weekly redistribution cadence (Sundays vs. Bi-Weekly) without editing crontab files.
- **Bandwidth Limits**: Configure office daytime upload throttling ($5\text{ MB/s}$) and off-peak speeds ($50\text{ MB/s}$).

### B. Job Telemetry & Error Inspector (Last X Days)
- Real-time tabular view of all sync, crawler, and redistribution jobs for the last 7, 14, or 30 days.
- Filter by status (`SUCCESS`, `WARNING`, `FAILED`).
- Expandable error logs showing file paths, error codes (e.g. API 429 quota, auth expiration), and a one-click **"Retry Failed"** button.

### C. Storage Telemetry & Headroom Gauge
- Live progress bar showing the 5 TB Google Drive quota utilization.
- Color-coded alerts: Green ($<70\%$), Yellow ($75\%$, Warning threshold), Red ($\ge 85\%$, Critical threshold).
- Categorical breakdown by domain and physical NAS node health.

### D. Conflict Resolution Center
- Displays active concurrent edits between LAN NAS and Google Drive.
- Provides one-click resolution buttons:
  * *Accept LAN Version as Canonical*
  * *Accept Cloud Version as Canonical*
  * *Keep Both as Versioned Siblings*
