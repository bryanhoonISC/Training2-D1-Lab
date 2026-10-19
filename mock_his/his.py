"""Mock hospital HIS: answers the D1 HL7 V2.5.1 queries over MLLP.

PAT-01, ZVIS01 (VIS-01), ZADM01 (ADM-01) and ZDIA01 (DIA-01), exactly as the
D1-Claim API spec V2.0.0 defines them. Run with --selftest to check it.
"""
import json
import os
import socketserver
import sys
import time

DATA = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), encoding="utf-8"))
PORT = 2575
VT, FS, CR = b"\x0b", b"\x1c", b"\x0d"


HOSP = DATA["hospital_code"]


def find(table, key, value):
    """First (id, row) in DATA[table] whose row[key] equals value."""
    return next(((k, r) for k, r in DATA[table].items() if value and r.get(key) == value), (None, None))


def short_pid(hn):
    return f"PID|1||{hn}^^^{HOSP}^MR"


def pat01(qpd):
    """PAT-01: QPD-3 = id^^^authority^type, type NI (citizen ID) or PP (passport)."""
    parts = (qpd[3] if len(qpd) > 3 else "").split("^") + [""] * 5
    ident, id_type = parts[0].replace("-", ""), parts[4]
    hn, p = find("patients", {"NI": "citizen_id", "PP": "passport_id"}.get(id_type, "-"), ident)
    if not p:
        return None
    ids = [f"{hn}^^^{HOSP}^MR"]
    if p["citizen_id"]:
        ids.append(f"{p['citizen_id']}^^^TH^NI")
    if p["passport_id"]:
        ids.append(f"{p['passport_id']}^^^TH^PP")
    a = p["address"]
    # PID-11 components as the spec field list numbers them: 1 street ... 6 country.
    address = "^".join([a.get("street", ""), "", a.get("city", ""), a.get("province", ""), a.get("zip", ""), a.get("country", "")])
    name = f"{p['family']}^{p['given']}^^^{p['prefix']}"
    return [f"PID|1||{'~'.join(ids)}||{name}||{p['birth_date']}|{p['gender']}|||{address}||{p['phone']}"]


def visit_number(qpd):
    """VIS/ADM/DIA-01: QPD-3 = id, QPD-4 = VN or AN. Return the VN, or None."""
    ident, id_type = (qpd + ["", "", "", "", ""])[3:5]
    if id_type == "VN":
        return ident if ident in DATA["visits"] else None
    if id_type == "AN":
        return DATA["admissions"].get(ident, {}).get("vn")
    return None


def vis01(qpd):
    vn = visit_number(qpd)
    if not vn:
        return None
    v, d = DATA["visits"][vn], DATA["visits"][vn]["physician"]
    segs = [short_pid(v["hn"]),
            f"ZVI|1|{vn}|{v['visit_date']}|{v['visit_type']}|{v['department_code']}|{v['department_name']}",
            f"ZCC|1|{v['chief_complaint']}"]
    segs += [f"PR1|{i}||{p['code']}^{p['name']}^{p['system']}" for i, p in enumerate(v["procedures"], 1)]
    segs.append(f"ZDR|1|{d['id']}|{d['family']}^{d['given']}^^^{d['prefix']}|{d['license']}")
    return segs


def adm01(qpd):
    vn = visit_number(qpd)
    an, a = find("admissions", "vn", vn)
    if not a:
        return None
    pv1 = ["PV1"] + [""] * 45
    pv1[1], pv1[2], pv1[3] = "1", "I", f"{a['ward']}^{a['room']}^{a['bed']}^{HOSP}"
    pv1[19], pv1[44], pv1[45] = vn, a["admit_date"], a["discharge_date"]
    return [short_pid(DATA["visits"][vn]["hn"]),
            "|".join(pv1).rstrip("|"),
            f"ZAD|1|{an}|{a['ward_type']}|{a['room_type']}|{a['expected_discharge']}"]


def dia01(qpd):
    vn = visit_number(qpd)
    if not vn:
        return None
    an, _ = find("admissions", "vn", vn)
    segs = [short_pid(DATA["visits"][vn]["hn"]), f"ZDI|1|{vn}|{an or ''}"]
    for i, d in enumerate(DATA["diagnoses"].get(vn, []), 1):
        dg1 = ["DG1"] + [""] * 15
        dg1[1], dg1[2], dg1[3] = str(i), d["method"], f"{d['code']}^{d['name']}^{d['system']}"
        dg1[6], dg1[15] = d["type"], d["priority"]
        segs.append("|".join(dg1))
    return segs


# QPD-1.1 query name -> (MSH-9 of the reply, segment builder)
QUERIES = {
    "PAT-01": ("RSP^K22^RSP_K21", pat01),
    "ZVIS01": ("RSP^ZV1^RSP_ZV1", vis01),
    "ZADM01": ("RSP^ZA1^RSP_ZA1", adm01),
    "ZDIA01": ("RSP^ZD1^RSP_ZD1", dia01),
}


def handle(message):
    """Take one QBP^Q22 message (str), return the RSP message (str)."""
    lines = [s for s in message.replace("\n", "\r").split("\r") if s]
    seg = {s.split("|")[0]: s for s in reversed(lines)}
    msh = (seg.get("MSH", "MSH") + "|" * 12).split("|")
    qpd_line = seg.get("QPD", "QPD")
    qpd = qpd_line.split("|")
    query_name, tag = (qpd + ["", ""])[1].split("^")[0], (qpd + ["", "", ""])[2]
    rsp_type, builder = QUERIES.get(query_name, ("ACK", None))
    out = [f"MSH|^~\\&|HIS|{msh[5]}|{msh[2]}|{msh[3]}|{time.strftime('%Y%m%d%H%M%S')}||{rsp_type}|RSP{msh[9]}|P|2.5.1"]
    if builder is None:
        out += [f"MSA|AE|{msh[9]}|Unknown query {query_name}", f"QAK|{tag}|AE|{qpd[1] if len(qpd) > 1 else ''}"]
        status = "AE"
    else:
        data = builder(qpd)
        status = "OK" if data else "NF"
        out += [f"MSA|AA|{msh[9]}", f"QAK|{tag}|{status}|{qpd[1]}", qpd_line] + (data or [])
    print(f"{query_name or '?'} {(qpd + ['', '', '', ''])[3]} -> {status}", flush=True)
    return "\r".join(out)


class MLLPHandler(socketserver.BaseRequestHandler):
    """Read VT ... FS CR frames on one connection, answer each one."""

    def handle(self):
        buffer = b""
        while chunk := self.request.recv(4096):
            buffer += chunk
            while FS + CR in buffer:
                frame, buffer = buffer.split(FS + CR, 1)
                reply = handle(frame.lstrip(VT).decode("utf-8"))
                self.request.sendall(VT + reply.encode("utf-8") + FS + CR)


def serve(port=PORT):
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), MLLPHandler) as server:
        print(f"HIS mock: MLLP on port {port}", flush=True)
        server.serve_forever()


def selftest():
    import socket
    import threading

    def query(name, ident, id_type, ctrl="T0001"):
        if name == "PAT-01":
            qpd = f"QPD|PAT-01^GetPatient^L|Q{ctrl}|{ident}^^^TH^{id_type}"
        else:
            title = {"ZVIS01": "GetVisit", "ZADM01": "GetAdmission", "ZDIA01": "GetDiagnosis"}.get(name, "Unknown")
            qpd = f"QPD|{name}^{title}^L|Q{ctrl}|{ident}|{id_type}|RAMA9"
        return f"MSH|^~\\&|D1_IRIS|D1|HIS|RAMA9|20261013124200||QBP^Q22^QBP_Q21|{ctrl}|P|2.5.1\r{qpd}\rRCP|I"

    def seg(rsp, name):
        return [s.split("|") for s in rsp.split("\r") if s.startswith(name + "|")]

    # PAT-01 by citizen ID: the HN and the CID come back in PID-3.
    rsp = handle(query("PAT-01", "3125800558898", "NI"))
    assert seg(rsp, "MSH")[0][8] == "RSP^K22^RSP_K21", rsp
    assert seg(rsp, "MSA")[0][1:3] == ["AA", "T0001"], rsp
    assert seg(rsp, "QAK")[0][2] == "OK", rsp
    pid = seg(rsp, "PID")[0]
    assert pid[3] == "HN00012345^^^RAMA9^MR~3125800558898^^^TH^NI", pid
    assert pid[5] == "Jaidee^Somchai^^^Mr." and pid[7] == "1990-05-15" and pid[8] == "M", pid

    # PAT-01 by passport ID.
    pid = seg(handle(query("PAT-01", "AB1234567", "PP")), "PID")[0]
    assert pid[3].startswith("HN00067890^^^RAMA9^MR~AB1234567^^^"), pid

    # Unknown ID: MSA AA, QAK NF, no PID.
    rsp = handle(query("PAT-01", "9999999999999", "NI"))
    assert seg(rsp, "MSA")[0][1] == "AA" and seg(rsp, "QAK")[0][2] == "NF" and not seg(rsp, "PID"), rsp

    # VIS-01 by VN: ZVI, ZCC, one PR1 per procedure, ZDR.
    rsp = handle(query("ZVIS01", "VN-2569-100300", "VN"))
    assert seg(rsp, "MSH")[0][8] == "RSP^ZV1^RSP_ZV1", rsp
    assert seg(rsp, "ZVI")[0][1:7] == ["1", "VN-2569-100300", "20261012083000", "IPD", "SUR", "General Surgery"], rsp
    assert seg(rsp, "ZCC")[0][2] == "Right lower abdominal pain", rsp
    assert [p[3] for p in seg(rsp, "PR1")] == ["PROC002^Laparoscopic appendectomy^99HIS", "PROC003^Abdominal ultrasound^99HIS"], rsp
    assert seg(rsp, "ZDR")[0][1:5] == ["1", "S67890", "Wongsa^Anan^^^Dr.", "67890"], rsp

    # VIS-01 by AN gives the same visit.
    assert seg(handle(query("ZVIS01", "AN00012345", "AN")), "ZVI")[0][2] == "VN-2569-100245"

    # ADM-01 by VN: PV1-3 location, PV1-19 VN, PV1-44 admit date, ZAD with Thai room type.
    rsp = handle(query("ZADM01", "VN-2569-100245", "VN"))
    assert seg(rsp, "MSH")[0][8] == "RSP^ZA1^RSP_ZA1", rsp
    pv1 = seg(rsp, "PV1")[0]
    assert pv1[2] == "I" and pv1[3] == "WARD01^^A01^RAMA9" and pv1[19] == "VN-2569-100245" and pv1[44] == "20260731090000", pv1
    assert seg(rsp, "ZAD")[0][1:6] == ["1", "AN00012345", "Medical Ward", "สามัญ ห้องรวม", "20260804120000"], rsp

    # DIA-01 by VN: ZDI, then one DG1 per diagnosis (DG1-2 method, DG1-3 code, DG1-6 type, DG1-15 priority).
    rsp = handle(query("ZDIA01", "VN-2569-100300", "VN"))
    assert seg(rsp, "MSH")[0][8] == "RSP^ZD1^RSP_ZD1", rsp
    assert seg(rsp, "ZDI")[0][1:4] == ["1", "VN-2569-100300", "AN00067890"], rsp
    dg1 = seg(rsp, "DG1")
    assert len(dg1) == 2 and dg1[0][2] == "ICD10CM" and dg1[0][3] == "K35.8^Acute appendicitis, other and unspecified^I10C", dg1
    assert dg1[0][6] == "A" and dg1[0][15] == "1" and dg1[1][15] == "2", dg1

    # Unknown query name: MSA AE.
    assert seg(handle(query("ZXXX01", "VN-2569-100245", "VN")), "MSA")[0][1] == "AE"

    # MLLP framing over a real socket, UTF-8 Thai text intact.
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), MLLPHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.create_connection(server.server_address, timeout=5) as sock:
        sock.sendall(VT + query("ZADM01", "AN00012345", "AN").encode("utf-8") + FS + CR)
        data = b""
        while not data.endswith(FS + CR):
            data += sock.recv(4096)
    server.shutdown()
    assert data.startswith(VT), data
    assert "สามัญ ห้องรวม" in data[1:-2].decode("utf-8"), data
    print("his selftest: all checks passed")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else serve()
