"""Draw the sequence overview of the lab flow: docs/Lab_Sequence_Overview.svg.

Three columns, one row for each step: the sequence diagram (left), the step and
its classes in call order (middle), and the IRIS flow: the production items in
call order, with sub-steps such as 2.1 for the hops inside IRIS (right).

Usage: python3 -I docs/tools/gen_overview_svg.py
"""
import os
from html import escape

SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
INK, MUTED, GREY, LINE = "#1F2328", "#57606A", "#8C959F", "#D0D7DE"

# Lifelines (x position, title, subtitle)
LANES = {
    "S": (80, "Hospital Staff", ""),
    "F": (265, "D1 Insureligent Hub", "(Front-End)"),
    "I": (480, "D1 Insureligent Hub", "(IRIS)"),
    "H": (690, "Hospital HIS", "(mock_his container)"),
    "P": (875, "Private Insurer", "(mock_insurer container)"),
}
X = {k: v[0] for k, v in LANES.items()}
W = 2480
T_NUM, T_STEP, T_CLS, T_END = 1050, 1088, 1398, 2220

TAGS = {
    "REST": ("#0969DA", "REST class: Insurligent.REST.*"),
    "MSG": ("#8250DF", "Message class: Insurligent.Interop.MSG.*"),
    "BS": ("#1A7F37", "Business service: Insurligent.Interop.BS.*"),
    "BP": ("#9A6700", "Business process (BPL): Insurligent.Interop.BP.*"),
    "DTL": ("#0E7490", "Data transformation: Insurligent.Interop.DTL.*"),
    "BO": ("#CF222E", "Business operation"),
    "HL7": ("#57606A", "HL7 message (standard schema 2.5.1)"),
    "MOCK": ("#8C959F", "Test system (not IRIS): mock_his/, mock_insurer/"),
}

UI_LINES = [("", "", "D1 Front only (no IRIS class)")]

ROWS = [
    {"kind": "section", "label": "Lab flow: GetPreAuthInfo_View, citizen ID (CID) search only"},
    {"kind": "ui", "frm": "S", "to": "F", "label": 'Input CID,\nclick "Search"', "step": ['Input CID, click "Search"']},
    {"kind": "msg", "frm": "F", "to": "I", "num": 1, "label": 'Send Request "GetPreAuthInfo_View"',
     "step": ['Send Request "GetPreAuthInfo_View"', "POST /api/insurligent/preauth/info"],
     "lines": [("REST", "Insurligent.REST.Router", "route POST /preauth/info, %JSONImport(), %ValidateObject()"),
               ("MSG", "Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest", "[ Required ] fields, search_type VALUELIST CID"),
               ("BS", "Insurligent.Interop.BS.D1FrontService", "item BS.GetPreAuthInfoView"),
               ("BP", "Insurligent.Interop.BP.GetPreAuthInfoView", "item BP.GetPreAuthInfoView")]},
    {"kind": "self", "at": "I", "num": 2, "label": "Transform data", "step": ["Transform data", "request -> PAT-01 query"],
     "lines": [("BP", "Insurligent.Interop.BP.GetPreAuthInfoView", "call BP.HIS.Patient"),
               ("MSG", "Insurligent.Interop.MSG.HIS.PatientRequest", "identity_no, hospital_code"),
               ("BP", "Insurligent.Interop.BP.HISPatient", "item BP.HIS.Patient (sub-BP)"),
               ("DTL", "Insurligent.Interop.DTL.PatientToQBP", "PatientRequest -> QBP^Q22"),
               ("HL7", "EnsLib.HL7.Message", "DocType 2.5.1:QBP_Q21")]},
    {"kind": "open", "id": "hl7", "label": "HL7 V2.X", "sub": "", "x1": X["I"] - 46, "x2": X["H"] + 110},
    {"kind": "xchg", "a": "I", "b": "H", "num": 3, "req": 'Send Request "PAT-01"', "rsp": 'Send Response "PAT-01"',
     "step": ["PAT-01", "QBP^Q22 -> RSP^K22"],
     "lines": [("BO", "EnsLib.HL7.Operation.TCPOperation", "item BO.HIS.HL7: MLLP mock_his:2575"),
               ("DTL", "Insurligent.Interop.DTL.RSPToPatient", "DocType 2.5.1:RSP_K22, QAK-2 -> 200 or 404"),
               ("MSG", "Insurligent.Interop.MSG.HIS.PatientResponse", "hospital number, name, birth date, gender"),
               ("MOCK", "mock_his/his.py", "answers PAT-01")]},
    {"kind": "close", "id": "hl7"},
    {"kind": "open", "id": "rest", "label": "Private Insurance, REST", "sub": "", "x1": X["I"] - 46, "x2": X["P"] + 96},
    {"kind": "xchg", "a": "I", "b": "P", "num": 4, "req": 'Send Request "Getinsurer"', "rsp": 'Response "Getinsurer"',
     "step": ["Getinsurer", "GET /api/insurer"],
     "lines": [("BP", "Insurligent.Interop.BP.GetPreAuthInfoView", 'if "Patient found?"'),
               ("MSG", "Insurligent.Interop.MSG.Insurer.GetInsurerRequest", "identity_type CID, company_code AIA"),
               ("BO", "Insurligent.Interop.BO.InsurerRest", "item BO.Insurer.REST: MessageMap -> GetInsurer()"),
               ("MSG", "Insurligent.Interop.MSG.Insurer.GetInsurerResponse", "insured_person: MSG.Type.InsuredPersonInfo"),
               ("MOCK", "mock_insurer/insurer.py", "GET /api/insurer")]},
    {"kind": "close", "id": "rest"},
    {"kind": "msg", "frm": "I", "to": "F", "num": 5, "dashed": True, "label": 'Send Response "GetPreAuthInfo_View"',
     "step": ['Send Response "GetPreAuthInfo_View"'],
     "lines": [("MSG", "Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewResponse", "patient, insurer_id, company_code"),
               ("BS", "Insurligent.Interop.BS.D1FrontService", "reply of item BS.GetPreAuthInfoView"),
               ("REST", "Insurligent.REST.Router", "%JSONExport() of the reply")]},
    {"kind": "ui", "frm": "F", "to": "S", "label": "Display Information", "step": ["Display Information"]},
]
FLOW = {
    1: [("1", "REST", "REST.Router", "400 if a field is missing or search_type is not CID", {"start": 1}),
        ("1.1", "BS", "BS.GetPreAuthInfoView", "SendRequestSync to BP.GetPreAuthInfoView, timeout 60 s", {}),
        ("1.2", "BP", "BP.GetPreAuthInfoView", "gets the GetPreAuthInfoViewRequest", {})],
    2: [("2", "BP", "BP.GetPreAuthInfoView", "call: a PatientRequest to the sub-BP", {}),
        ("2.1", "BP", "BP.HIS.Patient", "gets the PatientRequest", {}),
        ("2.2", "DTL", "DTL.PatientToQBP", "PatientRequest -> QBP^Q22 (MSH, QPD, RCP)", {})],
    3: [("3", "BO", "BO.HIS.HL7", "PAT-01 to the HIS over MLLP, RSP^K22 back", {}),
        ("3.1", "DTL", "DTL.RSPToPatient", "RSP -> PatientResponse. QAK-2 OK = 200, NF = 404", {}),
        ("3.2", "BP", "BP.GetPreAuthInfoView", "copies the patient into the reply", {}),
        ("3.3", "IF", "BP.GetPreAuthInfoView", "Patient found? Yes: 4. No: 5 (reply 404)", {})],
    4: [("4", "BO", "BO.Insurer.REST", "GetInsurer(): GET /api/insurer (CID, company AIA)", {}),
        ("4.1", "BP", "BP.GetPreAuthInfoView", "copies insurer_id and company_code into the reply", {})],
    5: [("5", "BS", "BS.GetPreAuthInfoView", "reply -> Insurligent.REST.Router -> JSON to D1 Front", {})],
}
FRAMES = {}

IF_COLOR = "#6E7781"
R_X, R_W = 2330, 560            # overview: x and width of the flow nodes
NH, NGAP = 40, 16               # overview: node height, gap between nodes

TITLE = "Lab: GetPreAuthInfo_View, sequence diagram -> classes"
HEAD_LINES = [
    'Subset of Healthcare-Claim_V7.00, page "Pre-Auth": a citizen ID (CID) search, the HL7 query PAT-01 and the REST call Getinsurer. '
    "Production Insurligent.Interop.Production, namespace INSURLIGENT.",
    "Numbered steps run in IRIS: the table gives their classes in call order. "
    "Grey steps run in D1 Front only. A request and its reply share one number.",
]
NOTES = [
    "• Build order in the lab (right to left): BO.HIS.HL7, BO.Insurer.REST, BP.HIS.Patient, BP.GetPreAuthInfoView, BS.GetPreAuthInfoView, Insurligent.REST.Router.",
    "• The answer key is in solution/src/ (class Insurligent.A.B is in solution/src/Insurligent/A/B.cls). Test it with solution/smoke.sh.",
]
SVG_TITLE = "Lab flow: sequence diagram to classes (Training2-D1-Lab)"

LH = 18  # table line height


def tw(s, size, mono=False):
    return len(s) * size * (0.61 if mono else 0.56)


def t(x, y, s, size=12, weight="normal", fill=INK, anchor="start", mono=False, style=""):
    fam = MONO if mono else SANS
    st = f' font-style="{style}"' if style else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{st}>{escape(s)}</text>')


def badge(cx, cy, n, r=11):
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="#0B4F9C" stroke="#FFFFFF" stroke-width="2"/>'
            + t(cx, cy + 4, str(n), 11, "bold", "#FFFFFF", "middle"))


def arrow(x1, x2, y, dashed=False, color=INK):
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    marker = "open" if dashed else ("grey" if color == GREY else "solid")
    pad = 3 if x2 > x1 else -3
    return (f'<line x1="{x1 + pad:.1f}" y1="{y:.1f}" x2="{x2 - pad:.1f}" y2="{y:.1f}" stroke="{color}" '
            f'stroke-width="1.6"{dash} marker-end="url(#{marker})"/>')


def table_height(row):
    lines = row.get("lines", UI_LINES if row["kind"] == "ui" else [])
    n = max(len(lines), len(row.get("step", [])))
    return 16 + n * LH


def flow_layout(num):
    """Overview: the y offset of each flow node in its row, and the height the nodes need."""
    y, pos = 12, []
    for sub, tag, title, detail, opt in FLOW.get(num, []):
        y += 26 * len(opt.get("open", []))
        pos.append(y)
        y += NH + 10 * len(opt.get("close", [])) + NGAP
    return pos, y


def flow_node(y, sub, tag, title, detail):
    color = IF_COLOR if tag == "IF" else TAGS[tag][0]
    dash = ' stroke-dasharray="5 3"' if tag == "IF" else ""
    out = [f'<rect x="{R_X}" y="{y}" width="{R_W}" height="{NH}" rx="7" fill="{"#F6F8FA" if tag == "IF" else "#FFFFFF"}" '
           f'stroke="{color}" stroke-width="1.4"{dash}/>']
    pw = len(sub) * 7 + 14
    out.append(f'<rect x="{R_X + 8}" y="{y + 11}" width="{pw}" height="18" rx="9" fill="{"#4F8FD9" if "." in sub else "#0B4F9C"}"/>')
    out.append(t(R_X + 8 + pw / 2, y + 24, sub, 11, "bold", "#FFFFFF", "middle"))
    tx = R_X + 8 + pw + 8
    out.append(f'<rect x="{tx}" y="{y + 12}" width="46" height="16" rx="8" fill="{color}"/>')
    out.append(t(tx + 23, y + 23.5, tag, 9.5, "bold", "#FFFFFF", "middle"))
    out.append(t(tx + 56, y + 17, title, 12, "normal", INK, mono=True))
    out.append(t(tx + 56, y + 33, detail, 11, "normal", MUTED))
    assert tx + 56 + tw(detail, 11) < R_X + R_W + 20, ("detail too long", sub)
    return out


DIAG_MIN = {"ui": 40, "msg": 50, "self": 50, "xchg": 74, "open": 30, "close": 14, "section": 38}


def main(out, overview=False):
    w = R_X + R_W + 50 if overview else W
    out_parts, bands, fg = [], [], []
    y = 168
    frames = {}
    for row in ROWS:
        k = row["kind"]
        h = DIAG_MIN[k] if k in ("open", "close", "section") else max(DIAG_MIN[k], table_height(row))
        if k == "ui" and "\n" in row["label"]:
            h += 14
        if overview and "num" in row:
            h = max(h, flow_layout(row["num"])[1])
        row["y"], row["h"] = y, h
        if k == "open":
            frames[row["id"]] = {"row": row, "top": y + 6}
        elif k == "close":
            frames[row["id"]]["bottom"] = y + 6
        y += h
    body_end = y + 10

    # Row bands and the table cells
    n_band = 0
    for row in ROWS:
        k, top, h = row["kind"], row["y"], row["h"]
        if k == "section":
            bands.append(f'<rect x="0" y="{top + 4}" width="{w}" height="{h - 8}" fill="#DDF4FF"/>')
            fg.append(t(24, top + h / 2 + 5, row["label"], 14, "bold", "#0A3069"))
            continue
        if k in ("open", "close"):
            continue
        if "num" in row:
            n_band += 1
            fill = "#F6F8FA" if n_band % 2 else "#FFFFFF"
            bands.append(f'<rect x="0" y="{top}" width="{w}" height="{h}" fill="{fill}"/>')
            bands.append(f'<line x1="{T_NUM - 12}" y1="{top + h}" x2="{w}" y2="{top + h}" stroke="{LINE}" stroke-width="1"/>')
            fg.append(badge(T_NUM + 12, top + 19, row["num"]))
        else:
            bands.append(f'<line x1="{T_NUM - 12}" y1="{top + h}" x2="{w}" y2="{top + h}" stroke="{LINE}" stroke-width="1" stroke-dasharray="2 3"/>')
        # step text
        for i, s in enumerate(row.get("step", [])):
            muted = k == "ui"
            fg.append(t(T_STEP, top + 23 + i * LH, s, 12.5 if i == 0 else 11.5,
                        "bold" if (i == 0 and not muted) else "normal",
                        GREY if muted else (INK if i == 0 else MUTED), style="italic" if muted else "",
                        mono=(i > 0 and s.startswith(("POST", "GET", "QBP")))))
        # class lines
        lines = row.get("lines", UI_LINES if k == "ui" else [])
        for i, (tag, main_text, note) in enumerate(lines):
            base = top + 23 + i * LH
            x = T_CLS
            if tag:
                color = TAGS[tag][0]
                fg.append(f'<rect x="{x}" y="{base - 12.5}" width="46" height="16" rx="8" fill="{color}"/>')
                fg.append(t(x + 23, base - 0.5, tag, 9.5, "bold", "#FFFFFF", "middle"))
            if main_text:
                fg.append(t(x + 56, base, main_text, 12, "normal", INK, mono=True))
                nx = x + 56 + tw(main_text, 12, True) + 12
            else:
                nx = x + 56
            if note:
                fg.append(t(nx, base, note, 11.5, "normal", GREY if k == "ui" else MUTED, style="italic" if k == "ui" else ""))

    # Lifelines
    lane_svg = []
    for key, (x, title, sub) in LANES.items():
        is_iris = key == "I"
        lane_svg.append(f'<rect x="{x - 78}" y="104" width="156" height="50" rx="7" '
                        f'fill="{"#DDF4FF" if is_iris else "#F6F8FA"}" stroke="{"#0969DA" if is_iris else "#8C959F"}" stroke-width="1.5"/>')
        lane_svg.append(t(x, 125 if sub else 134, title, 12.5, "bold", INK, "middle"))
        if sub:
            lane_svg.append(t(x, 142, sub, 11.5, "normal", MUTED, "middle"))
        lane_svg.append(f'<line x1="{x}" y1="154" x2="{x}" y2="{body_end}" stroke="{"#0969DA" if is_iris else "#8C959F"}" '
                        f'stroke-width="{1.6 if is_iris else 1.2}" stroke-dasharray="5 5"/>')

    # Frames
    frame_svg = []
    for f in frames.values():
        row, top, bottom = f["row"], f["top"], f["bottom"]
        x1, x2 = row["x1"], row["x2"]
        frame_svg.append(f'<rect x="{x1}" y="{top}" width="{x2 - x1}" height="{bottom - top}" fill="none" '
                         f'stroke="#57606A" stroke-width="1.3" rx="2"/>')
        label = row["label"]
        lw = tw(label, 11.5) + 18
        frame_svg.append(f'<path d="M{x1},{top} h{lw} v12 l-7,7 h{-(lw - 7)} z" fill="#EAEEF2" stroke="#57606A" stroke-width="1.1"/>')
        frame_svg.append(t(x1 + 7, top + 14, label, 11.5, "bold", INK))
        if row.get("sub"):
            frame_svg.append(t(x1 + lw + 10, top + 14, row["sub"], 11.5, "normal", MUTED, style="italic"))

    # Messages
    msg_svg = []
    for row in ROWS:
        k, top, h = row["kind"], row["y"], row["h"]
        if k in ("ui", "msg"):
            x1, x2 = X[row["frm"]], X[row["to"]]
            ya = top + max(30, h / 2 + 6)
            grey = k == "ui"
            msg_svg.append(arrow(x1, x2, ya, row.get("dashed", False), GREY if grey else INK))
            parts = row["label"].split("\n")
            for j, part in enumerate(parts):
                msg_svg.append(t((x1 + x2) / 2, ya - (7 if grey else 16) - (len(parts) - 1 - j) * 13, part,
                                 12 if not grey else 11.5, "normal", GREY if grey else INK, "middle",
                                 style="italic" if grey else ""))
            if not grey:
                bx = x1 + (16 if x2 > x1 else -16)
                msg_svg.append(badge(bx, ya, row["num"]))
        elif k == "xchg":
            xa, xb = X[row["a"]], X[row["b"]]
            mid = top + h / 2
            y1, y2 = mid - 6, mid + 24
            msg_svg.append(arrow(xa, xb, y1))
            msg_svg.append(arrow(xb, xa, y2, dashed=True))
            msg_svg.append(t((xa + xb) / 2 + 8, y1 - 9, row["req"], 12, "normal", INK, "middle"))
            msg_svg.append(t((xa + xb) / 2 + 8, y2 - 9, row["rsp"], 12, "normal", MUTED, "middle"))
            msg_svg.append(t(xb + 8, (y1 + y2) / 2 - 2, "Validate", 10.5, "normal", GREY, style="italic"))
            msg_svg.append(t(xb + 8, (y1 + y2) / 2 + 11, "+ Response", 10.5, "normal", GREY, style="italic"))
            msg_svg.append(badge(xa + 18, y1, row["num"]))
        elif k == "self":
            xa = X[row["at"]]
            label = row["label"]
            bw = tw(label, 12) + 22
            cy = top + h / 2
            msg_svg.append(f'<rect x="{xa + 14}" y="{cy - 14}" width="{bw}" height="28" rx="6" fill="#FFF8C5" stroke="#D4A72C" stroke-width="1.2"/>')
            msg_svg.append(t(xa + 14 + bw / 2, cy + 4.5, label, 12, "bold", "#4D2D00", "middle"))
            msg_svg.append(badge(xa - 17, cy, row["num"]))

    # Overview: the IRIS flow column
    flow_svg = []
    if overview:
        open_frames, frames_r, prev_bottom = [], [], None
        for row in ROWS:
            if "num" not in row:
                continue
            pos, _ = flow_layout(row["num"])
            for (sub, tag, title, detail, opt), dy in zip(FLOW[row["num"]], pos):
                ny = row["y"] + dy
                opens = opt.get("open", [])
                for i, fid in enumerate(opens):
                    open_frames.append((fid, ny - 26 * (len(opens) - i) + 4, len(open_frames)))
                if prev_bottom is not None and not opt.get("start"):
                    flow_svg.append(f'<line x1="{R_X + 30}" y1="{prev_bottom + 2}" x2="{R_X + 30}" y2="{ny - 3}" '
                                    f'stroke="{MUTED}" stroke-width="1.4" marker-end="url(#solid)"/>')
                flow_svg.extend(flow_node(ny, sub, tag, title, detail))
                prev_bottom = ny + NH
                for j, fid in enumerate(opt.get("close", [])):
                    ofid, ftop, depth = open_frames.pop()
                    assert ofid == fid, (ofid, fid)
                    frames_r.append((fid, ftop, ny + NH + 8 + 10 * j, depth))
        assert not open_frames, open_frames
        # Frames go under the nodes and arrows. The label tab is at the top right,
        # away from the arrows on the left.
        frame_r_svg = [f'<line x1="{R_X - 56}" y1="104" x2="{R_X - 56}" y2="{body_end}" stroke="{LINE}" stroke-width="2"/>']
        for fid, ftop, fbottom, depth in frames_r:
            x1, x2 = R_X - 36 + 12 * depth, R_X + R_W + 28 - 12 * depth
            label = FRAMES[fid]
            lw = tw(label, 11) + 18
            frame_r_svg.append(f'<rect x="{x1}" y="{ftop}" width="{x2 - x1}" height="{fbottom - ftop}" fill="none" '
                               f'stroke="#57606A" stroke-width="1.2" rx="3"/>')
            frame_r_svg.append(f'<path d="M{x2},{ftop} h{-lw} v12 l7,7 h{lw - 7} z" fill="#EAEEF2" stroke="#57606A" stroke-width="1"/>')
            frame_r_svg.append(t(x2 - lw + 11, ftop + 14, label, 11, "bold", INK))
        flow_svg = frame_r_svg + flow_svg

    # Header: title, column titles
    head = [
        t(24, 40, TITLE, 24, "bold", INK),
        t(24, 66, HEAD_LINES[0], 13, "normal", MUTED),
        t(24, 86, HEAD_LINES[1], 13, "normal", MUTED),
        f'<rect x="{T_NUM - 12}" y="104" width="{w - T_NUM + 12}" height="50" fill="#24292F" rx="4"/>',
        t(T_NUM + 12, 134, "#", 13, "bold", "#FFFFFF", "middle"),
        t(T_STEP, 134, "Step in the sequence diagram", 13, "bold", "#FFFFFF"),
        t(T_CLS, 134, "IRIS classes, in call order", 13, "bold", "#FFFFFF"),
    ]
    if overview:
        head[0] = t(24, 40, TITLE + " -> IRIS flow", 24, "bold", INK)
        head.append(t(R_X - 36, 134, "IRIS flow: production items, in call order (N.1, N.2 run inside IRIS after step N)", 13, "bold", "#FFFFFF"))

    # Footer: legend and notes
    foot, fy = [], body_end + 30
    foot.append(t(24, fy, "Legend", 14, "bold", INK))
    legend = list(TAGS.items()) + ([("IF", (IF_COLOR, "Decision in a BPL (if): dashed box"))] if overview else [])
    for i, (tag, (color, meaning)) in enumerate(legend):
        col, rown = i % 2, i // 2
        lx, ly = 24 + col * 470, fy + 26 + rown * 24
        foot.append(f'<rect x="{lx}" y="{ly - 12.5}" width="46" height="16" rx="8" fill="{color}"/>')
        foot.append(t(lx + 23, ly - 0.5, tag, 9.5, "bold", "#FFFFFF", "middle"))
        foot.append(t(lx + 56, ly, meaning, 12, "normal", INK))
    notes = ["Notes"] + NOTES
    if overview:
        notes.append("• Right column: the IRIS flow. Each box is a production item or class. N.1, N.2 run inside IRIS after step N. Frames are BPL loops.")
    nx0 = T_NUM - 12
    for i, s in enumerate(notes):
        foot.append(t(nx0, fy + i * 22, s, 14 if i == 0 else 12.5, "bold" if i == 0 else "normal", INK if i == 0 else MUTED))
    height = fy + max(26 + ((len(legend) + 1) // 2) * 24, 22 * len(notes)) + 30

    defs = (
        '<defs>'
        f'<marker id="solid" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>'
        f'<marker id="grey" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{GREY}"/></marker>'
        f'<marker id="open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10" fill="none" stroke="{INK}" stroke-width="1.6"/></marker>'
        '</defs>'
    )
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{height:.0f}" viewBox="0 0 {w} {height:.0f}">',
        f"<title>{escape(SVG_TITLE)}</title>",
        defs,
        f'<rect x="0" y="0" width="{w}" height="{height:.0f}" fill="#FFFFFF"/>',
        *bands,
        f'<line x1="{T_NUM - 26}" y1="104" x2="{T_NUM - 26}" y2="{body_end}" stroke="{LINE}" stroke-width="2"/>',
        *lane_svg, *frame_svg, *msg_svg, *flow_svg, *head, *fg, *foot,
        "</svg>",
    ]
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg) + "\n")
    print(f"wrote {out}: {w} x {height:.0f}, {sum(1 for r in ROWS if 'num' in r)} numbered steps")
    return w, height


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(os.path.join(here, "..", "Lab_Sequence_Overview.svg"), overview=True)
