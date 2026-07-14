#!/usr/bin/env bash
# Staging runbook executor — API evidence against live backend (localhost:8000).
set -euo pipefail

TENANT="11111111-1111-1111-1111-111111111111"
ADMIN_ID="3bad7c63-ae7a-4015-b8b9-b9d444a6d96d"
OWN_COMPANY="188b1b20-1948-4017-ada0-c0c838281e7b"
BASE="http://127.0.0.1:8000"
PREFIX="service_sales.targeted_advertising."
RUN_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LEAD_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
EXT_ID="staging-runbook-$(date +%s)"

TOKEN="$(docker exec hostflow-backend-1 python -c "
from backend.app.auth.jwt_tools import encode as encode_jwt
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc)
payload = {
    'sub': '$ADMIN_ID',
    'email': 'uos-rec-3bad7c63@hostflow.test',
    'role': 'administrator',
    'tenant_id': '$TENANT',
    'type': 'access',
    'iat': int(now.timestamp()),
    'exp': int((now + timedelta(minutes=120)).timestamp()),
}
print(encode_jwt(payload))
" 2>/dev/null | tail -1)"

AUTH=(-H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: $TENANT" -H "X-Own-Company-Id: $OWN_COMPANY" -H "Content-Type: application/json")

log() { echo "EVIDENCE|$1|$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$2")"; }

log run_at_utc "\"$RUN_AT\""
log tenant_id "\"$TENANT\""

docker exec hostflow-db-1 psql -U hostflow -d hostflow -q -c "
INSERT INTO leads (
  id, tenant_id, own_company_id, source, external_id, payload, normalized,
  status, stage, lead_type, lead_target_type
) VALUES (
  '$LEAD_ID', '$TENANT', '$OWN_COMPANY', 'meta_ads', '$EXT_ID',
  '{\"phone\": \"+48111222333\", \"full_name\": \"Staging Runbook\"}'::jsonb,
  '{\"full_name\": \"Staging Runbook\", \"phone\": \"+48111222333\", \"company_name\": \"Staging Runbook Sp. z o.o.\", \"email\": \"staging-runbook@example.com\"}'::jsonb,
  'new', 'new', 'client', 'client_lead'
);
"

log lead_id "\"$LEAD_ID\""
log sales_inquiry_path "\"/app/sales/inquiries/$LEAD_ID\""

PRE_SEND_CODE=$(curl -s -o /tmp/pre_send.json -w '%{http_code}' -X POST "$BASE/api/v1/leads/$LEAD_ID/questionnaire-invite" "${AUTH[@]}" -d '{"mark_sent": false}')
log step3_pre_send_post_status "$PRE_SEND_CODE"
log step3_pre_send_post_detail "$(python3 -c 'import json; print(json.dumps(json.load(open("/tmp/pre_send.json")).get("detail")))' 2>/dev/null || echo null)"

SEND_CODE=$(curl -s -o /tmp/send.json -w '%{http_code}' -X POST "$BASE/api/v1/leads/$LEAD_ID/questionnaire-invite" "${AUTH[@]}" -d '{"mark_sent": true}')
INVITE_TOKEN=$(python3 -c 'import json; print(json.load(open("/tmp/send.json")).get("token",""))')
APPLY_URL=$(python3 -c 'import json; b=json.load(open("/tmp/send.json")); print(b.get("apply_url") or ("/public/apply/" + str(b.get("token",""))))')
log step4_send_status "$SEND_CODE"
log step4_invite_token "\"$INVITE_TOKEN\""
log step4_apply_url "\"$APPLY_URL\""
log step4_invite_status "$(python3 -c 'import json; print(json.dumps(json.load(open("/tmp/send.json")).get("status")))' )"
log step4_sent_at "$(python3 -c 'import json; print(json.dumps(json.load(open("/tmp/send.json")).get("sent_at")))' )"

REFRESH_CODE=$(curl -s -o /tmp/refresh.json -w '%{http_code}' -X POST "$BASE/api/v1/leads/$LEAD_ID/questionnaire-invite" "${AUTH[@]}" -d '{"mark_sent": false}')
REFRESH_TOKEN=$(python3 -c 'import json; print(json.load(open("/tmp/refresh.json")).get("token",""))')
log step5_refresh_post_status "$REFRESH_CODE"
log step5_token_stable "$( [ "$REFRESH_TOKEN" = "$INVITE_TOKEN" ] && echo true || echo false )"
log step5_refresh_token "\"$REFRESH_TOKEN\""

curl -s -o /tmp/public.json "$BASE/api/v1/public/apply/$INVITE_TOKEN"
FIELD_COUNT=$(python3 -c 'import json; print(len(json.load(open("/tmp/public.json")).get("form_presentation",{}).get("fields",[])))')
SELECT_COUNT=$(python3 -c '
import json
fields=json.load(open("/tmp/public.json")).get("form_presentation",{}).get("fields",[])
print(sum(1 for f in fields if f.get("field_type") in ("single_select","multi_select")))
')
OPTIONS_NULL=$(python3 -c '
import json
fields=json.load(open("/tmp/public.json")).get("form_presentation",{}).get("fields",[])
sel=[f for f in fields if f.get("field_type") in ("single_select","multi_select")]
print("true" if sel and all(f.get("options") is None for f in sel) else "false")
')
log step6_public_field_count "$FIELD_COUNT"
log step6_select_field_count "$SELECT_COUNT"
log step6_api_options_null "$OPTIONS_NULL"

PAYLOAD=$(python3 <<'PY'
import json
prefix = "service_sales.targeted_advertising."
values = {
    f"{prefix}need_type": "client_acquisition",
    f"{prefix}primary_outcome": "more_inquiries",
    f"{prefix}promotion_subject": "service",
    f"{prefix}industry": "transport",
    f"{prefix}client_geo_scope": "poland",
    f"{prefix}conversion_destination": "whatsapp",
    f"{prefix}offer_ready": "ready",
    f"{prefix}marketing_materials": ["photos", "logo"],
    f"{prefix}prior_ads_experience": "no",
    f"{prefix}monthly_ad_budget": "2000_5000",
    f"{prefix}start_timeline": "two_weeks",
    f"{prefix}decision_maker": "owner",
    f"{prefix}contact_full_name": "Staging Runbook",
    f"{prefix}contact_company_name": "Staging Runbook Sp. z o.o.",
    f"{prefix}contact_phone": "+48111222333",
    f"{prefix}contact_email": "staging-runbook@example.com",
}
print(json.dumps(values))
PY
)
log step9_submit_payload_presentation_values "$PAYLOAD"

curl -s -o /tmp/put.json -w '%{http_code}' -X PUT "$BASE/api/v1/public/apply/$INVITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"presentation_values\": $PAYLOAD, \"application_kind\": \"client\"}}" > /tmp/put_code.txt

SUBMIT_CODE=$(curl -s -o /tmp/submit.json -w '%{http_code}' -X POST "$BASE/api/v1/public/apply/$INVITE_TOKEN/submit" \
  -H "Content-Type: application/json" \
  -d '{"consents": {"general": true, "employer_share": true, "terms_acceptance": true}, "cookies_accepted": true}')
log step9_submit_status "$SUBMIT_CODE"

curl -s -o /tmp/lead_after.json "$BASE/api/v1/leads/$LEAD_ID" "${AUTH[@]}"
python3 <<'PY' | while read -r line; do echo "$line"; done
import json
n=json.load(open("/tmp/lead_after.json")).get("normalized") or {}
sq=n.get("sales_questionnaire") or {}
print(f'EVIDENCE|step10_lead_questionnaire_status|{json.dumps(n.get("sales_questionnaire_status"))}')
print(f'EVIDENCE|step10_sales_questionnaire_summary|{json.dumps(sq)}')
print(f'EVIDENCE|step10_hidden_recruitment_roles_absent|{json.dumps("recruitment_roles" not in sq)}')
PY

INVITE_COUNT_BEFORE=$(docker exec hostflow-db-1 psql -U hostflow -d hostflow -t -A -c "SELECT count(*) FROM lead_questionnaire_invites WHERE lead_id='$LEAD_ID';")
POST_SUBMIT_CODE=$(curl -s -o /tmp/post_submit.json -w '%{http_code}' -X POST "$BASE/api/v1/leads/$LEAD_ID/questionnaire-invite" "${AUTH[@]}" -d '{"mark_sent": false}')
INVITE_COUNT_AFTER=$(docker exec hostflow-db-1 psql -U hostflow -d hostflow -t -A -c "SELECT count(*) FROM lead_questionnaire_invites WHERE lead_id='$LEAD_ID';")
log step10_post_submit_hydrate_status "$POST_SUBMIT_CODE"
log step10_invite_row_count_unchanged "$( [ "$INVITE_COUNT_BEFORE" = "$INVITE_COUNT_AFTER" ] && echo true || echo false )"
log step10_invite_row_count "$INVITE_COUNT_AFTER"

CONV1_CODE=$(curl -s -o /tmp/conv1.json -w '%{http_code}' -X POST "$BASE/api/v1/leads/$LEAD_ID/convert-client" "${AUTH[@]}" -d '{}')
CLIENT_ID_1=$(python3 -c 'import json; print(json.load(open("/tmp/conv1.json")).get("converted_client_id",""))')
log step11_convert1_status "$CONV1_CODE"
log step11_convert1_client_id "\"$CLIENT_ID_1\""

CONV2_CODE=$(curl -s -o /tmp/conv2.json -w '%{http_code}' -X POST "$BASE/api/v1/leads/$LEAD_ID/convert-client" "${AUTH[@]}" -d '{}')
CLIENT_ID_2=$(python3 -c 'import json; print(json.load(open("/tmp/conv2.json")).get("converted_client_id",""))')
log step12_convert2_status "$CONV2_CODE"
log step12_convert2_client_id "\"$CLIENT_ID_2\""
log step12_convert_idempotent "$( [ -n "$CLIENT_ID_1" ] && [ "$CLIENT_ID_1" = "$CLIENT_ID_2" ] && echo true || echo false )"

DEFECTS="[]"
python3 <<PY
import json
defects=[]
if "$PRE_SEND_CODE" != "404": defects.append(f"step3: expected 404 pre-send POST, got $PRE_SEND_CODE")
if "$SEND_CODE" != "200": defects.append(f"step4: send failed $SEND_CODE")
if "$REFRESH_TOKEN" != "$INVITE_TOKEN": defects.append("step5: token changed after refresh")
if "$SUBMIT_CODE" != "200": defects.append(f"step9: submit failed $SUBMIT_CODE")
n=json.load(open("/tmp/lead_after.json")).get("normalized") or {}
if n.get("sales_questionnaire_status") != "submitted": defects.append(f"step10: expected submitted, got {n.get('sales_questionnaire_status')}")
if "recruitment_roles" in (n.get("sales_questionnaire") or {}): defects.append("step10: hidden recruitment_roles leaked")
if "$INVITE_COUNT_BEFORE" != "$INVITE_COUNT_AFTER": defects.append("step10: invite row count changed after submit")
if "$CONV1_CODE" != "200" or not "$CLIENT_ID_1": defects.append(f"step11: convert failed $CONV1_CODE")
if "$CLIENT_ID_1" != "$CLIENT_ID_2": defects.append("step12: convert not idempotent")
print(f'EVIDENCE|defects|{json.dumps(defects)}')
print(f'EVIDENCE|staging_pass|{json.dumps(len(defects)==0)}')
PY
