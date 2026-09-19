# 10 — Disaster Recovery, Node Failure & Re-hydration Runbook

## 1. Architectural Resilience & Break-Glass Design

The primary architectural advantage of `gdrive-data-hub` is that **local NAS nodes are decoupled from data permanence**:
- Google Drive acts as the **central, off-site canonical ground truth**.
- Every authoritative document, personal record, code repository, and curated photo exists in the cloud with cryptographic verification in `catalog.db`.
- **A local NAS failure (disk failure, chassis burn, network cut, or site loss) causes zero permanent data loss.**

```
                                      ┌──────────────────────────────────────┐
                                      │        Google Drive Pro (5 TB)       │
                                      │        OFF-SITE CANONICAL TRUTH      │
                                      └──────────────────┬───────────────────┘
                                                         │
                         ┌───────────────────────────────┴───────────────────────────────┐
                         │                                                               │
                         ▼ (Cloud Break-Glass Access)                                    ▼ (One-Click Re-hydration)
              ┌─────────────────────┐                                         ┌─────────────────────┐
              │ Remote / Mobile     │                                         │ Replacement NAS     │
              │ Users (GDrive Web)  │                                         │ (Fresh Rebuild)     │
              └─────────────────────┘                                         └─────────────────────┘
```

---

## 2. Failure Scenarios & Recovery Procedures

### Scenario A: Transient Local Network Outage / ISP Cut
*Symptoms*: Office A or Office B loses internet connectivity; site-to-site VPN drops.
- **Immediate Impact**: Ingestion and redistribution sync pause automatically. Local LAN SMB/NFS access remains operational for office workers.
- **Remote Workers**: Workers away from the office continue working against Google Drive.
- **Recovery when Link Restores**:
  * The hub detects connection restoration.
  * Runs bidirectional conflict check (`gdrive-hub sync`).
  * If files were edited on both sides while offline, the "Never Overwrite, Always Branch" engine generates non-destructive versions (`<file>_lan_<ts>` and `<file>_gdrive_<ts>`) and logs them for review.

---

### Scenario B: Disk Degradation / Drive Failure on Local NAS
*Symptoms*: TrueNAS or Synology reports SMART errors or degraded pool (e.g. `192.168.0.167` `sdd` uncorrectable errors).
- **Procedure**:
  1. **Hot Replacement**: Swap the failing disk with a healthy drive.
  2. **Array Rebuild**:
     * Synology: DSM Storage Manager $\rightarrow$ Select Storage Pool $\rightarrow$ Repair $\rightarrow$ Select new drive.
     * TrueNAS: Storage $\rightarrow$ Pool Status $\rightarrow$ Select degraded disk $\rightarrow$ Replace $\rightarrow$ Select new drive.
  3. **Integrity Validation**:
     * Run scrub on the repaired pool.
     * Verify hashes against `catalog.db`:
       ```bash
       gdrive-hub verify --input "/mnt/truenas_167/Share/Critical_File.pdf"
       ```

---

### Scenario C: Catastrophic Hardware Destruction (Chassis Loss / Motherboard Fried)
*Symptoms*: An entire NAS unit (e.g. Synology DS220+ or TrueNAS bare-metal) is destroyed or completely non-bootable.

#### Step 1: Immediate Break-Glass Operation (RTO < 15 minutes)
Users do not wait for new hardware procurement:
1. Direct users to open **Google Drive Web** or mount **Google Drive for Desktop** (streaming drive).
2. All business folders (`01_BUSINESS/`), LifeOS documents (`02_LIFEOS_FAMILY/`), and project code (`03_PROJECTS_CODE/`) are instantly accessible and writable in the cloud.
3. Update local DNS alias if needed: point `storage-a.home.arpa` to a temporary local cache or cloud proxy.

#### Step 2: Provisioning Replacement Hardware
1. Procure or repurpose a replacement server or NAS chassis.
2. Install stable operating system (DSM on Synology or TrueNAS SCALE).
3. Create a redundant pool (RAID1 mirror or RAIDZ2) with $\ge 30\%$ free space headroom.
4. Create the standard share paths matching the role (e.g. `data/t1-biz` for Document NAS or `Share/Media` for Media NAS).

#### Step 3: One-Click Cloud Re-hydration (Full Restore)
Execute the re-hydration CLI to stream all canonical files back down from Google Drive:
```bash
# Re-hydrate Document NAS
gdrive-hub restore --role doc_nas --target "/mnt/new_nas/data"

# Re-hydrate Media NAS
gdrive-hub restore --role media_nas --target "/mnt/new_nas/Share/Media"
```
- The engine downloads all canonical files from Google Drive.
- Streams and computes local SHA-256 upon write, comparing against `catalog.db` to ensure zero transmission corruption.
- Automatically updates `source_instances` in `catalog.db` with the new local paths.

#### Step 4: Resume Production Traffic
1. Re-point service DNS alias: update `storage-a.home.arpa` $\rightarrow$ IP of replacement node.
2. Re-enable nightly automated ingest and weekly redistribution jobs.
3. Log the disaster recovery event in `job_runs`.

---

## 3. Disaster Recovery Metrics & SLAs

| Metric | Target SLA | Mechanism |
|---|---|---|
| **Recovery Point Objective (RPO)** | $\le 24\text{ hours}$ | Nightly automated delta ingest from LAN NAS to Google Drive. |
| **Break-Glass RTO (Cloud Access)** | $\le 15\text{ minutes}$ | Instant fallback to Google Drive Web / Google Drive Desktop. |
| **Full Physical Re-hydration RTO** | $4 - 8\text{ hours}$ | Automated `gdrive-hub restore` over high-speed link. |
| **Data Loss Tolerance** | **Zero** | Cryptographic SHA-256 catalog with cloud immutability. |
