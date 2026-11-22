#!/usr/bin/env bash
# Kill test: run a live case to its invitations, approve them, kill -9 the server in the middle of sending,
# restart it, and check that the local mailbox holds exactly one email per approved invitation.
# Needs Mailpit running (SMTP 1025, API 8025) and the keys in .env. Uses its own database and port.
# Usage: scripts/kill_test.sh [question]
set -u
cd "$(dirname "$0")/.."
PORT=8010
API="http://localhost:$PORT"
DB="$(mktemp -d)/kill_test.db"
QUESTION="${1:-How do quick-commerce companies in India run dark store operations?}"
export SYNEX_DB="$DB" SYNEX_SEND_DELAY_SECONDS=1.5
unset SYNEX_DEV_CACHE

start() { .venv/bin/uvicorn app.main:app --port $PORT > "$DB.log" 2>&1 & PID=$!; for _ in $(seq 1 30); do curl -s $API/health >/dev/null && return; sleep 0.5; done; }
state() { curl -s $API/customer/cases/$CID | python3 -c "import sys,json;print(json.load(sys.stdin)['state'])"; }
wait_for() { for _ in $(seq 1 120); do [ "$(state)" = "$1" ] && return 0; [ "$(state)" = "FAILED" ] && return 1; sleep 3; done; return 1; }

start
CID=$(curl -s -X POST $API/cases -H 'content-type: application/json' -d "{\"question\":\"$QUESTION\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "case $CID, database $DB"
wait_for PLANNED || { echo "FAIL: planning did not finish"; kill -9 $PID; exit 1; }
curl -s -X POST $API/customer/cases/$CID/approve-plan -H 'content-type: application/json' -d '{"panel_size": 2}' >/dev/null
wait_for AWAITING_APPROVAL || { echo "FAIL: sourcing did not finish"; kill -9 $PID; exit 1; }
REFS=$(curl -s $API/customer/cases/$CID | python3 -c "import sys,json;print(json.dumps([i['ref'] for i in json.load(sys.stdin)['invites'] if i['status']=='DRAFTED']))")
N=$(python3 -c "import json;print(len($REFS))")
echo "approving $N invitations, one every ${SYNEX_SEND_DELAY_SECONDS}s"
curl -s -X POST $API/customer/cases/$CID/approve-outreach -H 'content-type: application/json' -d "{\"refs\": $REFS}" >/dev/null &
sleep 2.2
SENT_BEFORE=$(sqlite3 "$DB" "select count(*) from outreach where case_id='$CID' and status='SENT'" 2>/dev/null || python3 -c "import sqlite3;print(sqlite3.connect('$DB').execute(\"select count(*) from outreach where case_id='$CID' and status='SENT'\").fetchone()[0])")
kill -9 $PID
echo "killed the server (kill -9) with $SENT_BEFORE of $N sent"
sleep 1
unset SYNEX_SEND_DELAY_SECONDS
start
echo "restarted"
sleep 8
python3 - "$DB" "$CID" <<'PY'
import json, sqlite3, sys, urllib.request
db, cid = sys.argv[1], sys.argv[2]
c = sqlite3.connect(db)
keys = {k: t for k, t in c.execute("select key, target_id from actions where case_id=?", (cid,))}
approved = [r[0] for r in c.execute("select id from outreach where case_id=? and decided_by='customer' and status!='REJECTED'", (cid,))]
msgs = json.load(urllib.request.urlopen("http://localhost:8025/api/v1/messages?limit=1000"))["messages"]
counts = {k: sum(1 for m in msgs if (m.get("MessageID") or "").strip("<>") == f"{k}@synex.local") for k in keys}
statuses = dict(c.execute("select status, count(*) from outreach where case_id=? group by status", (cid,)).fetchall())
print("outreach statuses after restart:", statuses)
print("emails in the mailbox per invitation:", sorted(counts.values()))
ok = len(keys) == len(approved) and all(n == 1 for n in counts.values())
print("PASS: every approved invitation is in the mailbox exactly once" if ok else "FAIL")
sys.exit(0 if ok else 1)
PY
RESULT=$?
kill $PID 2>/dev/null
exit $RESULT
