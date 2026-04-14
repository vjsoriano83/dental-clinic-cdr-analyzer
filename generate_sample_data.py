"""
Generate synthetic CDR data that mimics real Asterisk/FreePBX behavior.
Each incoming call generates multiple records (queue + ring group),
linked by a shared linkedid — just like a real PBX.

Author: Victor Soriano Tarrega (@vjsoriano83)
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# ── Ring group: extensions that ring when a call enters queue 251 ──
RING_GROUP = ["201", "221", "224", "225"]

# ── Weighted hour distribution (business hours) ──
HOUR_WEIGHTS = {
    8: 3, 9: 7, 10: 10, 11: 9, 12: 8,
    13: 5, 14: 10, 15: 6, 16: 7, 17: 8,
    18: 5, 19: 2,
}

# ── Real disposition ratios (per unique call, post-dedup) ──
CALL_DISPOSITIONS = {
    "ANSWERED": 0.84,
    "NO ANSWER": 0.15,
    "BUSY": 0.01,
}

NUM_CALLS = 500
START_DATE = datetime(2025, 11, 1)
END_DATE = datetime(2025, 11, 30)
OUTPUT_FILE = "data/sample_cdr.csv"

FIELDS = [
    "calldate", "clid", "src", "dst", "dcontext", "channel",
    "dstchannel", "lastapp", "lastdata", "duration", "billsec",
    "disposition", "amaflags", "accountcode", "uniqueid",
    "userfield", "did", "cnum", "cnam", "outbound_cnum",
    "outbound_cnam", "dst_cnam", "recordingfile", "linkedid",
    "peeraccount", "sequence",
]


def random_phone():
    prefix = random.choice(["612", "634", "651", "672", "698", "617", "645"])
    return f"+34{prefix}{random.randint(100000, 999999)}"


def random_date():
    day_offset = random.randint(0, (END_DATE - START_DATE).days)
    date = START_DATE + timedelta(days=day_offset)
    while date.weekday() >= 5:
        day_offset = random.randint(0, (END_DATE - START_DATE).days)
        date = START_DATE + timedelta(days=day_offset)
    hours = list(HOUR_WEIGHTS.keys())
    weights = list(HOUR_WEIGHTS.values())
    hour = random.choices(hours, weights=weights, k=1)[0]
    return date.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def make_record(calldate, phone, dst, dcontext, disposition, duration, billsec, lastapp, linked_id, seq, channel, dstchannel=""):
    unique_id = f"{int(calldate.timestamp())}.{random.randint(100000, 999999)}"
    return {
        "calldate": calldate.strftime("%Y-%m-%d %H:%M:%S"),
        "clid": f'"""{phone}"" <{phone}>',
        "src": phone, "dst": dst, "dcontext": dcontext,
        "channel": channel, "dstchannel": dstchannel,
        "lastapp": lastapp,
        "lastdata": f"{dst}@default" if lastapp in ("Dial", "Queue") else "",
        "duration": duration, "billsec": billsec,
        "disposition": disposition, "amaflags": 3,
        "accountcode": "", "uniqueid": unique_id,
        "userfield": "", "did": "s" if dcontext == "ext-queues" else "",
        "cnum": phone, "cnam": phone,
        "outbound_cnum": "", "outbound_cnam": "", "dst_cnam": "",
        "recordingfile": "", "linkedid": linked_id,
        "peeraccount": "", "sequence": seq,
    }


def generate_call(seq_start):
    """Generate all CDR records for a single real call."""
    calldate = random_date()
    phone = random_phone()
    linked_id = f"{int(calldate.timestamp())}.{random.randint(100000, 999999)}"
    channel = f"SIP/trunk-{random.randint(1000, 9999):04x}"

    # Decide call outcome
    outcome = random.choices(
        list(CALL_DISPOSITIONS.keys()),
        weights=list(CALL_DISPOSITIONS.values()), k=1
    )[0]

    records = []
    seq = seq_start

    if outcome == "ANSWERED":
        answering_ext = random.choice(RING_GROUP)
        talk_duration = random.randint(15, 300)
        ring_duration = random.randint(5, 20)

        # Queue records (one per ring group member)
        for ext in RING_GROUP:
            disp = "ANSWERED" if ext == answering_ext else "NO ANSWER"
            dur = talk_duration + ring_duration if ext == answering_ext else ring_duration
            bill = talk_duration if ext == answering_ext else 0
            dstch = f"Local/{ext}@from-queue-{random.randint(10000,99999):05x};1"
            records.append(make_record(calldate, phone, "251", "ext-queues", disp, dur, bill, "Queue", linked_id, seq, channel, dstch))
            seq += 1

        # ext-local records (one per ring group member)
        for ext in RING_GROUP:
            disp = "ANSWERED" if ext == answering_ext else "NO ANSWER"
            dur = talk_duration if ext == answering_ext else ring_duration
            bill = talk_duration if ext == answering_ext else 0
            dstch = f"PJSIP/{ext}-{random.randint(10000,99999):05x}" if ext == answering_ext else ""
            records.append(make_record(calldate, phone, ext, "ext-local", disp, dur, bill, "Dial", linked_id, seq, f"Local/{ext}@from-queue-{random.randint(10000,99999):05x};1", dstch))
            seq += 1

    elif outcome == "NO ANSWER":
        ring_duration = random.randint(15, 45)

        for ext in RING_GROUP:
            dstch = f"Local/{ext}@from-queue-{random.randint(10000,99999):05x};1"
            records.append(make_record(calldate, phone, "251", "ext-queues", "NO ANSWER", ring_duration, 0, "Queue", linked_id, seq, channel, dstch))
            seq += 1

        for ext in RING_GROUP:
            records.append(make_record(calldate, phone, ext, "ext-local", "NO ANSWER", ring_duration, 0, "Dial", linked_id, seq, f"Local/{ext}@from-queue-{random.randint(10000,99999):05x};1"))
            seq += 1

    else:  # BUSY
        records.append(make_record(calldate, phone, "251", "ext-queues", "BUSY", 0, 0, "Queue", linked_id, seq, channel))
        seq += 1

    return records, seq


def main():
    all_records = []
    seq = 1
    for _ in range(NUM_CALLS):
        records, seq = generate_call(seq)
        all_records.extend(records)

    all_records.sort(key=lambda r: r["calldate"], reverse=True)

    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_records)

    # Summary
    from collections import Counter
    linked_ids = set(r["linkedid"] for r in all_records)
    call_outcomes = Counter()
    by_linked = {}
    for r in all_records:
        if r["linkedid"] not in by_linked:
            by_linked[r["linkedid"]] = []
        by_linked[r["linkedid"]].append(r)

    for lid, recs in by_linked.items():
        disps = set(r["disposition"] for r in recs)
        if "ANSWERED" in disps:
            call_outcomes["ANSWERED"] += 1
        elif "BUSY" in disps:
            call_outcomes["BUSY"] += 1
        else:
            call_outcomes["NO ANSWER"] += 1

    print(f"✅ Generated {len(all_records)} CDR records from {NUM_CALLS} real calls → {OUTPUT_FILE}")
    print(f"   Records per call: {len(all_records)/NUM_CALLS:.1f} avg")
    print(f"   ANSWERED: {call_outcomes['ANSWERED']}  |  NO ANSWER: {call_outcomes['NO ANSWER']}  |  BUSY: {call_outcomes['BUSY']}")


if __name__ == "__main__":
    main()
