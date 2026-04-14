# CDR Data Format

This folder contains Call Detail Records (CDR) exported from an Asterisk/FreePBX phone system.

## Sample Data

`sample_cdr.csv` contains 500 synthetic calls (3,965 raw CDR records) generated with realistic patterns based on a real dental clinic PBX configuration.

## Field Description

| Field | Description | Example |
|-------|-------------|---------|
| `calldate` | Call timestamp | 2025-11-15 10:23:45 |
| `src` | Caller number | +34612345678 |
| `dst` | Destination (extension or number) | 251 |
| `disposition` | Call result | ANSWERED / NO ANSWER / BUSY / FAILED |
| `duration` | Total duration in seconds | 45 |
| `billsec` | Actual talk time in seconds | 30 |
| `dcontext` | Asterisk dial context | ext-queues / ext-local / from-internal |
| `channel` | SIP channel used | SIP/trunk-001a |
| `linkedid` | Groups all records from the same real call | 1731654225.123456 |
| `cnam` | Caller name (if available) | V-Recepcion 1 |

## Important: Deduplication Required

A single incoming call generates **multiple CDR records** (7-8 on average) because the PBX queue rings several extensions simultaneously. All records from the same call share the same `linkedid`. The analysis pipeline deduplicates by grouping on this field to get one row per real call.

## Using Your Own Data

1. Export CDRs from FreePBX: **Reports → CDR Reports → Download CSV**
2. Place your CSV files in this folder (e.g., `1T.csv`, `2T.csv`)
3. Run: `python3 main.py "data/*.csv"`

Your real data files are excluded from Git via `.gitignore` — they will never be uploaded to GitHub.