#!/usr/bin/env bash
# Checks of the answer key, in the order of the lab: each BO, each BP, then
# end to end through REST. Run solution/load.sh first.
set -uo pipefail
cd "$(dirname "$0")/.."
BASE=${BASE:-http://localhost:52773/api/insurligent}
AUTH=${AUTH:-_SYSTEM:SYS}
failed=0

check() {  # check <label> <text> <expected substring>
  if grep -qF -- "$3" <<<"$2"; then echo "PASS $1"; else echo "FAIL $1"; echo "     got: ${2:0:600}"; failed=$((failed + 1)); fi
}
post() { curl -s -u "$AUTH" -H 'Content-Type: application/json' --data-binary "$2" "$BASE$1"; }
iris() { docker compose exec -T iris iris session IRIS -U INSURLIGENT; }

echo "--- 1. BOs (Test button: EnsLib.Testing.Service)"
r=$(iris <<'EOF'
set req=##class(Insurligent.Interop.MSG.HIS.PatientRequest).%New(),req.IdentityNo="3-1258-00558-89-8",req.HospitalCode="RAMA9"
set sc=##class(Insurligent.Interop.DTL.PatientToQBP).Transform(req,.qbp) write !,"QBP: ",$Translate(qbp.OutputToString(),$Char(13),"~"),!
set sc=##class(EnsLib.Testing.Service).SendTestRequest("BO.HIS.HL7",qbp,.rsp,,1) write !,"HL7BO: ",$System.Status.IsOK(sc)," ",$Select($IsObject($Get(rsp)):$Translate(rsp.OutputToString(),$Char(13),"~"),1:$System.Status.GetErrorText(sc)),!
set g=##class(Insurligent.Interop.MSG.Insurer.GetInsurerRequest).%New(),g.IdentityType="CID",g.IdentityNo="3-1258-00558-89-8",g.CompanyCode="AIA"
set sc=##class(EnsLib.Testing.Service).SendTestRequest("BO.Insurer.REST",g,.ir,,1) write !,"RESTBO: ",$System.Status.IsOK(sc)," ",ir.ResponseCode," ",ir.InsuredPerson.InsurerId," ",ir.InsuredPerson.Age,!
set g.IdentityNo="9999999999999" set sc=##class(EnsLib.Testing.Service).SendTestRequest("BO.Insurer.REST",g,.ir,,1) write !,"RESTBO404: ",$System.Status.IsOK(sc)," ",ir.ResponseCode,!
halt
EOF
)
check "DTL PatientToQBP: QPD-3 is the CID without dashes, type NI" "$r" "QPD|PAT-01^GetPatient^L|QPAT"
check "DTL PatientToQBP: QPD-3" "$r" "|3125800558898^^^TH^NI~RCP|I"
check "BO.HIS.HL7: PAT-01 reply with the patient" "$r" "HL7BO: 1 MSH|"
check "BO.HIS.HL7: reply has PID" "$r" "PID|1||HN00012345"
check "BO.Insurer.REST: Getinsurer 200, INS123456, age as a number" "$r" "RESTBO: 1 200 INS123456 36"
check "BO.Insurer.REST: unknown person, 404 as data" "$r" "RESTBO404: 1 404"

echo "--- 2. BPs"
r=$(iris <<'EOF'
set req=##class(Insurligent.Interop.MSG.HIS.PatientRequest).%New(),req.IdentityNo="3-1258-00558-89-8",req.HospitalCode="RAMA9"
set sc=##class(EnsLib.Testing.Service).SendTestRequest("BP.HIS.Patient",req,.p,,1) write !,"SUBBP: ",$System.Status.IsOK(sc)," ",p.ResponseCode," ",p.FirstName," ",p.LastName," ",p.HospitalNumber," ",p.Gender,!
set req.IdentityNo="9999999999999" set sc=##class(EnsLib.Testing.Service).SendTestRequest("BP.HIS.Patient",req,.p,,1) write !,"SUBBP404: ",$System.Status.IsOK(sc)," ",p.ResponseCode,!
set v=##class(Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest).%New(),v.SearchType="CID",v.IdentityNo="3-1258-00558-89-8",v.HospitalCode="RAMA9"
set sc=##class(EnsLib.Testing.Service).SendTestRequest("BP.GetPreAuthInfoView",v,.r,,1) write !,"MAINBP: ",$System.Status.IsOK(sc)," ",r.ResponseCode," ",r.FirstName," ",r.InsurerId," ",r.CompanyCode,!
halt
EOF
)
check "BP.HIS.Patient: PAT-01 found" "$r" "SUBBP: 1 200 Somchai Jaidee HN00012345 M"
check "BP.HIS.Patient: unknown CID, 404" "$r" "SUBBP404: 1 404"
check "BP.GetPreAuthInfoView: patient and insurer" "$r" "MAINBP: 1 200 Somchai INS123456 AIA"

echo "--- 3. End to end: POST $BASE/preauth/info"
r=$(post /preauth/info '{"search_type":"CID","identity_no":"3-1258-00558-89-8","hospital_code":"RAMA9"}')
check "CID: response 200" "$r" '"response_code":"200"'
check "CID: patient from PAT-01" "$r" '"first_name":"Somchai"'
check "CID: insurer from Getinsurer" "$r" '"insurer_id":"INS123456"'
check "PID: 400, search_type must be CID" "$(post /preauth/info '{"search_type":"PID","identity_no":"AB1234567","hospital_code":"RAMA9"}')" 'search_type'
check "no identity_no: 400" "$(post /preauth/info '{"search_type":"CID","hospital_code":"RAMA9"}')" '"response_code":"400"'
check "unknown CID: 404" "$(post /preauth/info '{"search_type":"CID","identity_no":"9999999999999","hospital_code":"RAMA9"}')" '"response_code":"404"'

echo "---"
if [ "$failed" -eq 0 ]; then echo "SOLUTION SMOKE TEST PASSED"; else echo "SOLUTION SMOKE TEST FAILED: $failed check(s)"; exit 1; fi
