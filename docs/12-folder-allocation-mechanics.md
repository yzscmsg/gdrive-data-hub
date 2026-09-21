# 12 — Folder Classification & Allocation Mechanics

**Date:** 2026-09-21  
**Status:** Approved & Active Implementation  
**Companion Doc:** `nas-arch/docs/09-folder-classification-and-allocation-mechanics.md`

---

## 1. The 3-Tier Allocation Engine

The `gdrive-data-hub` engine determines folder category, authority, and replication target through three hierarchical tiers:

```
[New or Migrating Folder]
          │
          ▼
   1. Path Inheritance Check (Does path match 00_Inbox .. 06_Platform?)
          ├── YES ──► Assign Root Archetype (ACTIVE_WORKSPACE, COLD_ARCHIVE, etc.)
          └── NO
               │
               ▼
   2. Semantic Heuristic Engine (hub/classifier/rules.py)
          ├── Keyword match (Business / Archive / Media / Tools)
          └── ModTime analysis (fresh <= 180d, stable, lack_of_update, obsolete)
               │
               ▼
   3. Explicit Policy Override (folder_policies SQLite table)
          └── Supersedes automated scoring if a custom rule exists
```

---

## 2. Satellite Edge Cache Eligibility (TrueNAS 167)

To preserve Synology as the single master station while offering high-speed LAN access in Office B:

* **Target Path**: `\\192.168.0.167\169ftpshare\fast-workspace`
* **Eligibility Rule**:
  $$\text{Sync to 167 if: } (\text{domain} \in \{\text{'business'}, \text{'knowledge'}\} \land \text{status} = \text{'fresh'}) \lor (\text{domain} = \text{'software'} \land \text{category} \in \{\text{'software'}, \text{'doc'}\})$$
* **Storage Limit**: 50 GB ceiling with LRU auto-eviction.

---

## 3. SQLite Database Representation

Folder policies are stored in `catalog.db` under `folder_policies`:

```sql
SELECT folder_prefix, archetype, tier, authority_node, replica_target, sync_frequency
FROM folder_policies;
```

When files are crawled, they are associated with their canonical root and lifecycle record.
