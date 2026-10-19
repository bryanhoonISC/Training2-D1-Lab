"""Mock private insurer: the D1 insurer REST APIs, as the D1-Claim spec V2.0.0 defines them.

  GET  /api/insurer         Getinsurer             identity_type, identity_no, company_code
  GET  /api/policy          GetPolicy              insurer_id, company_code
  GET  /api/benefit         GetBenefit             policy_number, company_code
  POST /api/preauth         PostPreAuth (SubmitPreAuth), JSON body
  GET  /api/preauth/status  GetPreAuthStatus_Sync  admission_number, company_code

The spec puts a body on GET (defect SD-11). This mock reads the GET fields from
the query string. Run with --selftest to check it.
"""
import itertools
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DATA = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), encoding="utf-8"))
PORT = 8080


STEPS = ["Pre-Authorize Submitted", "Waiting for Medical", "Pre-Accepted"]
REJECT_ABOVE = 500000  # ponytail: one fixed rule; make it per-benefit if the demo needs real adjudication
PREAUTHS = {}  # (admission_number, company_code) -> submission record, in memory only
LOCK = threading.Lock()
CASES = itertools.count(1)


def envelope(code, message, **fields):
    return code, {"response_code": str(code), "response_message": message, **fields}


def missing(params, *names):
    lack = [n for n in names if not params.get(n)]
    return envelope(400, "Missing: " + ", ".join(lack)) if lack else None


def dashed(cid):
    """3125800558898 -> 3-1258-00558-89-8 (the JSON form in the spec samples)."""
    return f"{cid[0]}-{cid[1:5]}-{cid[5:10]}-{cid[10:12]}-{cid[12]}" if len(cid) == 13 else cid


def get_insurer(p):
    if err := missing(p, "identity_type", "identity_no", "company_code"):
        return err
    key = {"CID": "citizen_id", "PID": "passport_id"}.get(p["identity_type"])
    if not key:
        return envelope(400, "identity_type must be CID or PID")
    ident = p["identity_no"].replace("-", "") if key == "citizen_id" else p["identity_no"]
    who = next((i for i in DATA["insured"] if i["company_code"] == p["company_code"] and i[key] == ident), None)
    if not who:
        return envelope(404, f"No insured person {p['identity_no']} at {p['company_code']}")
    return envelope(200, "Success", insured_person={
        "insurer_id": who["insurer_id"], "insurer_citizenId": dashed(who["citizen_id"]) or None,
        "insurer_passportId": who["passport_id"] or None, "insurer_title": who["title"],
        "insurer_firstname": who["firstname"], "insurer_lastName": who["lastname"],
        "insurer_gender": who["gender"], "insurer_age": who["age"]})


def get_policy(p):
    if err := missing(p, "insurer_id", "company_code"):
        return err
    found = [{k: v for k, v in pol.items() if k not in ("company_code", "insurer_id")}
             for pol in DATA["policies"] if pol["company_code"] == p["company_code"] and pol["insurer_id"] == p["insurer_id"]]
    if not found:
        return envelope(404, f"No policy for {p['insurer_id']} at {p['company_code']}")
    return envelope(200, "Success", insurer={"company_code": p["company_code"],
                                             "company_name": DATA["companies"][p["company_code"]]}, policies=found)


def get_benefit(p):
    if err := missing(p, "policy_number", "company_code"):
        return err
    if not any(pol["policy_number"] == p["policy_number"] and pol["company_code"] == p["company_code"] for pol in DATA["policies"]):
        return envelope(404, f"No policy {p['policy_number']} at {p['company_code']}")
    return envelope(200, "Success", benefits=DATA["benefits"].get(p["policy_number"], []))


def post_preauth(body):
    if not isinstance(body, dict):
        return envelope(400, "Body must be a JSON object")
    needed = ["hospital_code", "person.hospital_number", "insurer.company_code", "insurer.insurer_id",
              "policies.policy_number", "admission.admission_number"]
    lack = [n for n in needed if not lookup(body, n)]
    if lack:
        return envelope(400, "Missing: " + ", ".join(lack))
    an, cc = lookup(body, "admission.admission_number"), lookup(body, "insurer.company_code")
    cost = float(str(lookup(body, "admission.estimated_cost") or 0).replace(",", ""))
    with LOCK:
        PREAUTHS[(an, cc)] = {"case": f"PA-{time.strftime('%Y')}-{next(CASES):06d}", "step": 0, "cost": cost,
                              "submit_date": body.get("submit_date") or time.strftime("%Y-%m-%d %H:%M:%S")}
    return envelope(200, "Success", auth_status=STEPS[0])


def get_preauth_status(p):
    if err := missing(p, "admission_number", "company_code"):
        return err
    with LOCK:
        rec = PREAUTHS.get((p["admission_number"], p["company_code"]))
        if not rec:
            return envelope(404, f"No pre-auth for {p['admission_number']} at {p['company_code']}")
        rec["step"] = min(rec["step"] + 1, len(STEPS) - 1)
        status = STEPS[rec["step"]]
        if rec["step"] == len(STEPS) - 1 and rec["cost"] > REJECT_ABOVE:
            status = "Rejected"
    return envelope(200, "Success", claim_case_number=rec["case"], claim_status=status, submit_date=rec["submit_date"])


def lookup(obj, dotted):
    for part in dotted.split("."):
        obj = obj.get(part) if isinstance(obj, dict) else None
    return obj


GETS = {"/api/insurer": get_insurer, "/api/policy": get_policy, "/api/benefit": get_benefit,
        "/api/preauth/status": get_preauth_status}


def route(method, path, params, body):
    """Return (HTTP status, JSON-able dict) for one request."""
    if method == "GET" and path in GETS:
        return GETS[path](params)
    if method == "POST" and path == "/api/preauth":
        return post_preauth(body)
    return envelope(404, f"Unknown path {method} {path}")


class Handler(BaseHTTPRequestHandler):
    def respond(self):
        url = urlparse(self.path)
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            return self.send(*envelope(400, "Body is not valid JSON"))
        if self.command == "GET" and isinstance(body, dict):
            params.update({k: str(v) for k, v in body.items()})  # the spec's GET-with-body form also works
        self.send(*route(self.command, url.path.rstrip("/"), params, body))

    do_GET = do_POST = respond

    def send(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_request(self, code="-", size="-"):
        print(f"{self.command} {self.path} -> {code}", flush=True)


def serve(port=PORT):
    with ThreadingHTTPServer(("0.0.0.0", port), Handler) as server:
        print(f"Insurer mock: HTTP on port {port}", flush=True)
        server.serve_forever()


def selftest():
    import threading
    import urllib.error
    import urllib.request

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/api"

    def call(path, body=None):
        req = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                                     data=json.dumps(body).encode("utf-8") if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    # Getinsurer: dashed CID matches; the envelope carries response_code.
    status, body = call("/insurer?identity_type=CID&identity_no=3-1258-00558-89-8&company_code=AIA")
    assert status == 200 and body["response_code"] == "200", body
    assert body["insured_person"]["insurer_id"] == "INS123456" and body["insured_person"]["insurer_age"] == 36, body
    # Not insured with this company: 404 envelope.
    status, body = call("/insurer?identity_type=CID&identity_no=3125800558898&company_code=DEMO")
    assert status == 404 and body["response_code"] == "404", body
    # Passport holder at DEMO.
    status, body = call("/insurer?identity_type=PID&identity_no=AB1234567&company_code=DEMO")
    assert status == 200 and body["insured_person"]["insurer_passportId"] == "AB1234567", body
    # Missing parameter: 400.
    status, body = call("/insurer?identity_type=CID&company_code=AIA")
    assert status == 400 and body["response_code"] == "400", body

    # GetPolicy: company plus every policy of the insured person.
    status, body = call("/policy?insurer_id=INS123456&company_code=AIA")
    assert status == 200 and body["insurer"]["company_name"].startswith("American International"), body
    assert [p["policy_number"] for p in body["policies"]] == ["AIA-TH-998821", "AIA-TH-998822"], body

    # GetBenefit: benefits with their coverage items; Thai remark intact.
    status, body = call("/benefit?policy_number=AIA-TH-998821&company_code=AIA")
    assert status == 200 and body["benefits"][0]["benefit_code"] == "IPD", body
    assert body["benefits"][0]["remaining_amount"] == 45000.0, body
    assert body["benefits"][0]["coverage_items"][0]["remark"] == "ต่อวัน", body

    # PostPreAuth (SubmitPreAuth) then GetPreAuthStatus_Sync: one step per call.
    submission = {"hospital_code": "RAMA9",
                  "person": {"hospital_number": "HN00012345", "visit_number": "VN-2569-100245"},
                  "insurer": {"company_code": "AIA", "insurer_id": "INS123456"},
                  "policies": {"policy_number": "AIA-TH-998821"},
                  "admission": {"admission_number": "AN00012345", "estimated_cost": "10000.00"},
                  "submit_date": "2026-07-09 10:00:15"}
    status, body = call("/preauth", submission)
    assert status == 200 and body["auth_status"] == "Pre-Authorize Submitted", body
    status, body = call("/preauth/status?admission_number=AN00012345&company_code=AIA")
    assert status == 200 and body["claim_status"] == "Waiting for Medical", body
    assert body["claim_case_number"].startswith("PA-") and body["submit_date"] == "2026-07-09 10:00:15", body
    assert call("/preauth/status?admission_number=AN00012345&company_code=AIA")[1]["claim_status"] == "Pre-Accepted"
    assert call("/preauth/status?admission_number=AN00012345&company_code=AIA")[1]["claim_status"] == "Pre-Accepted"

    # Estimated cost above 500,000 ends at Rejected.
    big = json.loads(json.dumps(submission))
    big["admission"] = {"admission_number": "AN-BIG", "estimated_cost": 600000}
    assert call("/preauth", big)[0] == 200
    call("/preauth/status?admission_number=AN-BIG&company_code=AIA")
    assert call("/preauth/status?admission_number=AN-BIG&company_code=AIA")[1]["claim_status"] == "Rejected"

    # Unknown pre-auth: 404. Missing admission in the body: 400. Unknown path: 404.
    assert call("/preauth/status?admission_number=AN-NONE&company_code=AIA")[0] == 404
    bad = json.loads(json.dumps(submission))
    del bad["admission"]
    status, body = call("/preauth", bad)
    assert status == 400 and "admission.admission_number" in body["response_message"], body
    assert call("/nothing")[0] == 404

    server.shutdown()
    print("insurer selftest: all checks passed")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else serve()
