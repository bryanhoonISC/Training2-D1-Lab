"""Build the lab handouts as Word files, in the look of docs/reference/*.docx.

  docs/Environment_Setup_Worksheet.docx   (template: docs/reference/Environment_Setup_Worksheet.docx)
  docs/Lab_Handout.docx                   (template: docs/reference/Day1_Lab_Handout 1.docx)

The script keeps the styles, numbering, header, footer and page set-up of each
template, and writes a new body with the same paragraph and table patterns.
Code snippets come from the answer key in solution/src/Insurligent/.
Diagrams: the SVGs become PNG images with headless Google Chrome.
docs/reference/ is not in Git: copy the reference documents there first.

Usage: python3 -I docs/tools/build_handouts.py
"""
import html
import os
import re
import struct
import subprocess
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(ROOT, "docs", "reference")
SOL = os.path.join(ROOT, "solution", "src", "Insurligent")
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# ---------------------------------------------------------------- XML patterns (from the reference files)
CALIBRI = '<w:rFonts w:ascii="Calibri" w:cs="Calibri" w:eastAsia="Calibri" w:hAnsi="Calibri"/>'
CONSOLAS = '<w:rFonts w:ascii="Consolas" w:cs="Consolas" w:eastAsia="Consolas" w:hAnsi="Consolas"/>'
INK = "333F48"
BORDER = "C9D1D6"
TEAL = "00A99D"
BAND = "F1F4F6"


def esc(s):
    return html.escape(s, quote=False)


def run(text, bold=False, code=False, italic=False, size=21, color=INK):
    if code:
        size, color = (size - 2), "6B2C91"
    rpr = (CONSOLAS if code else CALIBRI) + ("<w:b/><w:bCs/>" if bold else "") + ("<w:i/><w:iCs/>" if italic else "")
    rpr += f'<w:color w:val="{color}"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def rich(text, size=21, color=INK, bold=False):
    """Runs for text with **bold** and `code` parts."""
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**"):
            out.append(run(part[2:-2], bold=True, size=size, color=color))
        elif part.startswith("`"):
            out.append(run(part[1:-1], code=True, size=size, color=color))
        else:
            out.append(run(part, bold=bold, size=size, color=color))
    return "".join(out)


def p(text, after=120):
    return f'<w:p><w:pPr><w:spacing w:after="{after}"/></w:pPr>{rich(text)}</w:p>'


def check(text):
    return p(f"**Check:** {text}")


def title(text):
    return f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:rPr>{CALIBRI}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'


def subtitle(text):
    return f'<w:p><w:pPr><w:spacing w:after="240"/></w:pPr>{run(text, italic=True, size=22, color="5F6B76")}</w:p>'


def h1(text):
    return f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:rPr>{CALIBRI}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'


def h2(text):
    return f'<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:rPr>{CALIBRI}</w:rPr><w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'


def bullet(text):
    return (f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr>'
            f'<w:spacing w:after="60"/></w:pPr>{rich(text)}</w:p>')


def code(lines):
    """Grey code block, one paragraph per line (the spacing pattern of the reference)."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    out, last = [], len(lines) - 1
    for i, line in enumerate(lines):
        before = 80 if i == 0 else 0
        after = 160 if i == last else 0
        out.append(f'<w:p><w:pPr><w:shd w:fill="F3F3F3" w:color="auto" w:val="clear"/>'
                   f'<w:spacing w:after="{after}" w:before="{before}" w:line="260"/><w:ind w:left="120" w:right="120"/></w:pPr>'
                   f'<w:r><w:rPr>{CONSOLAS}<w:color w:val="{INK}"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
                   f'<w:t xml:space="preserve">{esc(line)}</w:t></w:r></w:p>')
    return "".join(out)


def table(header, rows, widths):
    """Teal header row, then white and grey rows. widths in DXA; they set the table width."""
    total = sum(widths)
    borders = "".join(f'<w:{s} w:val="single" w:color="{BORDER}" w:sz="4"/>' for s in ("top", "left", "bottom", "right"))
    mar = ('<w:tcMar><w:top w:type="dxa" w:w="60"/><w:left w:type="dxa" w:w="100"/>'
           '<w:bottom w:type="dxa" w:w="60"/><w:right w:type="dxa" w:w="100"/></w:tcMar>')

    def cell(text, width, fill, head):
        color = "FFFFFF" if head else INK
        return (f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{width}"/><w:tcBorders>{borders}</w:tcBorders>'
                f'<w:shd w:fill="{fill}" w:color="auto" w:val="clear"/>{mar}</w:tcPr>'
                f'<w:p>{rich(text, size=19, color=color, bold=head)}</w:p></w:tc>')

    xml = [f'<w:tbl><w:tblPr><w:tblW w:type="dxa" w:w="{total}"/><w:tblBorders>'
           + "".join(f'<w:{s} w:val="single" w:color="auto" w:sz="4"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
           + '</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>'
           + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"]
    xml.append('<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(cell(t, w, TEAL, True) for t, w in zip(header, widths)) + "</w:tr>")
    for i, r in enumerate(rows):
        fill = "FFFFFF" if i % 2 == 0 else BAND
        xml.append('<w:tr><w:trPr><w:tblHeader w:val="false"/></w:trPr>' + "".join(cell(t, w, fill, False) for t, w in zip(r, widths)) + "</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml) + p("", after=60)


IMAGES = []  # (relationship id, png path)


def image(png, width_twips, caption=None):
    rid = f"rIdTr{len(IMAGES) + 1}"
    IMAGES.append((rid, png))
    with open(png, "rb") as fh:
        w, h = struct.unpack(">II", fh.read(24)[16:24])
    cx = width_twips * 635
    cy = int(cx * h / w)
    n = 100 + len(IMAGES)
    pic = (f'<w:p><w:pPr><w:spacing w:after="80"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
           f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
           f'<wp:docPr id="{n}" name="Picture {n}"/><wp:cNvGraphicFramePr>'
           f'<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
           f'</wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
           f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
           f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr>'
           f'<pic:cNvPr id="{n}" name="image{n}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
           f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr>'
           f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
           f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
           f'</wp:inline></w:drawing></w:r></w:p>')
    if caption:
        pic += f'<w:p><w:pPr><w:spacing w:after="160"/><w:jc w:val="center"/></w:pPr>{run(caption, italic=True, size=18, color="5F6B76")}</w:p>'
    return pic


# ---------------------------------------------------------------- solution snippets
def snippet(rel):
    """A class from the solution, without the Storage block that IRIS adds."""
    with open(os.path.join(SOL, rel), encoding="utf-8") as fh:
        text = fh.read()
    text = re.sub(r"\nStorage Default\n\{.*?\n\}\n", "\n", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"
    return code(text.rstrip("\n").split("\n"))


# ---------------------------------------------------------------- diagrams
def svg_to_png(svg, png, scale=2):
    with open(svg, encoding="utf-8") as fh:
        w, h = map(int, re.search(r'width="(\d+)" height="(\d+)"', fh.read()).groups())
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "view.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(f'<!doctype html><html><body style="margin:0"><img style="display:block" width="{w}" height="{h}" src="file://{svg}"></body></html>')
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        f"--force-device-scale-factor={scale}", f"--window-size={w},{h}", f"--screenshot={png}", f"file://{page}"],
                       check=True, capture_output=True, timeout=120)


def systems_svg(path):
    """The systems of the training environment: Docker with three containers, VS Code and a REST client."""
    S = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

    def box(x, y, w, h, fill, stroke, rx=10, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"{d}/>'

    def txt(x, y, s, size=16, weight="normal", fill="#1F2328", anchor="start"):
        return f'<text x="{x}" y="{y}" font-family="{S}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'

    def arrow(x1, y1, x2, y2, label="", lx=None, ly=None):
        out = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#1F2328" stroke-width="2" marker-end="url(#a)"/>'
        if label:
            out += txt(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 8, label, 14, "normal", "#57606A", "middle")
        return out

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="640" viewBox="0 0 1100 640">',
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#1F2328"/></marker></defs>',
        '<rect width="1100" height="640" fill="#FFFFFF"/>',
        box(10, 10, 1080, 620, "#FFFFFF", "#8C959F", 14, "8 6"), txt(30, 42, "Your computer", 20, "bold"),
        box(30, 60, 210, 90, "#F6F8FA", "#8C959F"), txt(135, 98, "VS Code", 18, "bold", anchor="middle"),
        txt(135, 124, "edit and compile classes", 14, anchor="middle", fill="#57606A"),
        box(30, 180, 210, 90, "#F6F8FA", "#8C959F"), txt(135, 218, "Browser / Postman", 18, "bold", anchor="middle"),
        txt(135, 244, "Management Portal, REST", 14, anchor="middle", fill="#57606A"),
        box(300, 60, 770, 550, "#EAF6FF", "#0969DA", 14), txt(320, 92, "Docker (docker compose up -d)", 18, "bold", fill="#0A3069"),
        box(330, 110, 400, 300, "#FFFFFF", "#0969DA"), txt(350, 142, "iris", 20, "bold", fill="#0A3069"),
        txt(350, 168, "InterSystems IRIS for Health", 15, fill="#57606A"),
        txt(350, 196, "localhost:52773  Portal and REST APIs", 15), txt(350, 220, "localhost:9091   superserver", 15),
        box(350, 238, 360, 156, "#F6F8FA", "#57606A", 8), txt(366, 264, "Namespace INSURLIGENT", 15, "bold"),
        txt(366, 296, "Insurligent.Interop.Production", 14), txt(366, 318, "  you build it in the lab", 13, fill="#57606A"),
        txt(366, 352, "src/Insurligent/...", 14), txt(366, 374, "  your classes, compiled from VS Code", 13, fill="#57606A"),
        box(800, 110, 250, 130, "#FFFFFF", "#9A6700"), txt(925, 146, "mock_his", 20, "bold", anchor="middle", fill="#4D2D00"),
        txt(925, 174, "Hospital system (HIS)", 15, anchor="middle"), txt(925, 198, "HL7 v2.5.1 over MLLP", 15, anchor="middle", fill="#57606A"),
        txt(925, 222, "port 2575", 15, anchor="middle", fill="#57606A"),
        box(800, 280, 250, 130, "#FFFFFF", "#CF222E"), txt(925, 316, "mock_insurer", 20, "bold", anchor="middle", fill="#82071E"),
        txt(925, 344, "Private insurer", 15, anchor="middle"), txt(925, 368, "REST and JSON", 15, anchor="middle", fill="#57606A"),
        txt(925, 392, "port 8080", 15, anchor="middle", fill="#57606A"),
        arrow(240, 105, 328, 160, "port 52773", 284, 120), arrow(240, 225, 328, 250, "port 52773", 284, 226),
        arrow(730, 165, 798, 165, "PAT-01", 764, 155), arrow(730, 345, 798, 345, "Getinsurer", 764, 335),
        txt(330, 450, "The containers find each other by name: IRIS sends HL7 to mock_his:2575", 15),
        txt(330, 474, "and REST calls to mock_insurer:8080. The two mocks are small Python", 15),
        txt(330, 498, "programs with test data (mock_his/data.json, mock_insurer/data.json).", 15),
        txt(330, 540, "Ports on your computer: 52773, 9091, 2575, 8080 (localhost only).", 15, "bold"),
        "</svg>",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))


# ---------------------------------------------------------------- docx assembly
def build(template, out, header_text, body, doc_title):
    zin = zipfile.ZipFile(template)
    doc = zin.read("word/document.xml").decode("utf-8")
    start = doc.index("<w:body>") + len("<w:body>")
    sect = re.search(r"<w:sectPr>(?:(?!<w:sectPr>).)*?</w:sectPr>\s*</w:body>", doc, re.S).group(0)
    sect = sect[:sect.rindex("</w:body>")]
    # The schema puts w:cols before w:docGrid. One template has them the other way round.
    cols = re.search(r"<w:cols\b[^>]*/>", sect)
    if cols and sect.index(cols.group(0)) > sect.find("<w:docGrid"):
        sect = sect.replace(cols.group(0), "").replace("<w:docGrid", cols.group(0) + "<w:docGrid")
    landscape = (sect.replace('w:w="11906" w:h="16838" w:orient="portrait"', 'w:w="16838" w:h="11906" w:orient="landscape"'))
    content = body.replace("<!--SECT:portrait-->", f"<w:p><w:pPr>{sect}</w:pPr></w:p>").replace(
        "<!--SECT:landscape-->", f"<w:p><w:pPr>{landscape}</w:pPr></w:p>")
    new_doc = doc[:start] + content + sect + "</w:body></w:document>"
    rels = zin.read("word/_rels/document.xml.rels").decode("utf-8")
    hdr_rel = re.search(r'Id="([^"]+)"[^>]*Target="(header\d+\.xml)"', rels) or re.search(r'Target="(header\d+\.xml)"[^>]*Id="([^"]+)"', rels)
    header_part = "word/" + [g for g in hdr_rel.groups() if g.endswith(".xml")][0]
    extra_rels = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                         f'Target="media/tr_image{i + 1}.png"/>' for i, (rid, _) in enumerate(IMAGES))
    rels = rels.replace("</Relationships>", extra_rels + "</Relationships>")
    ctypes = zin.read("[Content_Types].xml").decode("utf-8")
    if 'Extension="png"' not in ctypes:
        ctypes = ctypes.replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = new_doc.encode("utf-8")
            elif item.filename == "word/_rels/document.xml.rels":
                data = rels.encode("utf-8")
            elif item.filename == "[Content_Types].xml":
                data = ctypes.encode("utf-8")
            elif item.filename == header_part:
                data = re.sub(r"(<w:t[^>]*>)[^<]*(</w:t>)", lambda m: m.group(1) + esc(header_text) + m.group(2), data.decode("utf-8"), count=1).encode("utf-8")
            elif item.filename == "docProps/core.xml":
                text = data.decode("utf-8")
                text = re.sub(r"<dc:title>[^<]*</dc:title>", f"<dc:title>{esc(doc_title)}</dc:title>", text)
                data = text.encode("utf-8")
            zout.writestr(item, data)
        for i, (rid, png) in enumerate(IMAGES):
            with open(png, "rb") as fh:
                zout.writestr(f"word/media/tr_image{i + 1}.png", fh.read())
    print(f"wrote {os.path.relpath(out, ROOT)}: {len(IMAGES)} image(s)")


# ---------------------------------------------------------------- content
PORTRAIT_W, LANDSCAPE_W = 9638, 14570      # text width in DXA (A4, 2 cm margins)
PORTAL = "http://localhost:52773/csp/sys/UtilHome.csp"
CID_BODY = ['{', '  "search_type": "CID",', '  "identity_no": "3-1258-00558-89-8",', '  "hospital_code": "RAMA9"', '}']


def environment_body(systems_png):
    b = [
        title("Environment Set-up Worksheet"),
        subtitle("DataOne / Insureligent Training · Interoperability · Before the lab"),
        p("Do this worksheet before the interoperability lab. It takes about 30 minutes, plus the time to download the IRIS image (several GB)."),
        p("When you finish, you have:", after=60),
        bullet("IRIS for Health running on your computer, in a Docker container"),
        bullet("the `INSURLIGENT` namespace, ready for the production that you build in the lab"),
        bullet("two test systems: a hospital system (HIS) that answers HL7, and an insurer that answers REST"),
        bullet("VS Code connected to `INSURLIGENT`"),
        bullet("a REST client"),
        p("If a step fails, write down the step number and the error, and tell your instructor before the lab."),

        h1("1. What you need"),
        p("Install these first:"),
        table(["Software", "Why"], [
            ["Docker Desktop (or any Docker with Compose v2)", "Runs IRIS and the two test systems. You do not need to install IRIS."],
            ["Git", "Downloads the lab environment."],
            ["Visual Studio Code", "Where you write and compile your classes."],
            ["A REST client, for example Postman", "Calls the API that you build."],
        ], [3800, 5838]),
        p("Login for everything in this course:"),
        table(["Setting", "Value"], [["Username", "_SYSTEM"], ["Password", "SYS"], ["Namespace", "INSURLIGENT"]], [3800, 5838]),

        h1("2. Get the lab environment"),
        p("Your instructor gives you access to the repository. Open a terminal. Go to the folder where you keep your projects. Run:"),
        code(["git clone https://github.com/bryanhoonISC/Training2-D1-Lab.git", "cd Training2-D1-Lab"]),
        p("You now have a folder called `Training2-D1-Lab`. Run all the `docker compose` commands in this worksheet inside this folder."),

        h1("3. Start the environment"),
        p("**3.1 Start the containers.** The first time, this downloads the IRIS image and builds everything. It can take a long time."),
        code(["docker compose up -d --build"]),
        p("**3.2 Watch the set-up.** It creates the namespace and loads the classes in `src/`. At the start of the lab, `src/` has only empty package folders."),
        code(["docker compose logs -f iris"]),
        p("Wait until you see this line:"),
        code(["[insurligent-setup] complete."]),
        p("Then press Ctrl-C. This stops showing the log. IRIS keeps running."),
        p("If the line does not appear, see Section 9."),

        h1("4. The systems"),
        p("`docker compose up -d` starts three containers. The picture shows them, and the tools on your computer that you use with them."),
        image(systems_png, PORTRAIT_W, "The lab environment: three containers in Docker, and the tools you use."),
        table(["Container", "What it is", "Port on your computer"], [
            ["iris", "InterSystems IRIS for Health: the Management Portal, the REST APIs and the production", "52773 (web), 9091 (superserver)"],
            ["mock_his", "Test hospital system (HIS). It answers HL7 queries such as PAT-01, over MLLP.", "2575"],
            ["mock_insurer", "Test insurer. It answers REST calls such as Getinsurer, with JSON.", "8080"],
        ], [1700, 5338, 2600]),
        p("The two test systems are small Python programs, not real systems. They answer with the test data in `mock_his/data.json` and `mock_insurer/data.json`."),
        p("Inside IRIS, the namespace `INSURLIGENT` has no production yet. In the lab, you build `Insurligent.Interop.Production`."),

        h1("5. Check IRIS"),
        p(f"**5.1 Open the Management Portal.** In your browser, go to `{PORTAL}`. Log in with `_SYSTEM` / `SYS`."),
        p("**5.2 Check the namespace.** Go to System Administration › Configuration › System Configuration › Namespaces. `INSURLIGENT` must be in the list."),
        p("**5.3 Check interoperability.** Go to Interoperability. If IRIS asks for a namespace, choose `INSURLIGENT`. Then go to List › Productions. The list is empty: you create the production in the lab."),

        h1("6. Check the test systems"),
        p("**6.1 Run the self-test of each mock.**"),
        code(["docker compose exec mock_his python /app/his.py --selftest", "docker compose exec mock_insurer python /app/insurer.py --selftest"]),
        p("The last lines must be:"),
        code(["his selftest: all checks passed", "insurer selftest: all checks passed"]),
        p("**6.2 Call the insurer directly.** In your browser or REST client, send:"),
        code(["GET http://localhost:8080/api/insurer?identity_type=CID&identity_no=3-1258-00558-89-8&company_code=AIA"]),
        p('You should get `"response_code": "200"` and an `insured_person` with `"insurer_id": "INS123456"`. No login is necessary for the mock.'),

        h1("7. Set up VS Code"),
        p("**7.1 Install the extensions.** In VS Code, install the InterSystems ObjectScript Extension Pack. It lets you edit IRIS classes and compile them on the server."),
        p("**7.2 Open the lab folder.** Click File › Open Folder and choose the `Training2-D1-Lab` folder."),
        p("**7.3 Connect VS Code to IRIS.** The folder already has the file `.vscode/settings.json`:"),
        code(['{', '  "intersystems.servers": {', '    "insurligent": {', '      "webServer": { "host": "localhost", "port": 52773 },',
              '      "username": "_SYSTEM"', '    }', '  },', '  "objectscript.conn": { "server": "insurligent", "ns": "INSURLIGENT", "active": true }', '}']),
        p("When VS Code asks for a password, enter `SYS`."),
        p("**7.4 Check the connection.** Click the InterSystems icon in the Activity Bar, then the Explorer view. It shows the classes in `INSURLIGENT` on the server. You should see the `Insurligent` package with one class, `Insurligent.Setup`."),
        p("**7.5 Look at the folders.** In the Explorer of VS Code, open `src/Insurligent`. It has an empty folder for each package that you write in the lab, for example `Interop/BO` and `Interop/MSG/Insurer`."),

        h1("8. Stop and start"),
        p("Stop the containers when you finish. Give IRIS time to shut down cleanly:"),
        code(["docker compose down -t 60"]),
        p("Start them again. IRIS keeps your work:"),
        code(["docker compose up -d"]),
        p("On the day of the lab, start them before the class starts."),

        h1("9. If something goes wrong"),
        table(["Problem", "What to do"], [
            ["`[insurligent-setup] complete.` never appears", "Read the whole log: `docker compose logs iris`."],
            ["A port is in use (52773, 9091, 2575 or 8080)", "Another program or another IRIS environment uses it. Stop that one first (for example `docker compose down` in its folder)."],
            ["On Linux: IRIS cannot write to `/dur`", "Run `sudo chown -R 51773:51773 data/durable`, then `docker compose up -d` again."],
            ["You want to start over completely", "`docker compose down -t 60`, then move the folder `data/durable/iris_conf.d` out of the project, then `docker compose up -d --build`."],
            ["Anything else", "Write down the step and the error, and tell your instructor."],
        ], [3800, 5838]),

        h1("10. Checklist"),
        p("Tick each line. Bring this to the lab."),
        table(["Done", "Check"], [
            ["☐", "The log shows `[insurligent-setup] complete.`"],
            ["☐", "I can log in to the Management Portal as `_SYSTEM`."],
            ["☐", "`INSURLIGENT` exists, and its Interoperability menu opens."],
            ["☐", "Both mock self-tests pass, and the insurer answers in 6.2."],
            ["☐", "VS Code shows `Insurligent.Setup` in the InterSystems Explorer view, and the empty folders under `src/Insurligent`."],
        ], [900, 8738]),
    ]
    return "".join(b)


def dtl_table(rel):
    """The Set actions of a DTL class from the solution, as a table (target, value)."""
    with open(os.path.join(SOL, rel), encoding="utf-8") as fh:
        text = fh.read()
    rows = [[f"`{html.unescape(prop)}`", f"`{html.unescape(val)}`"]
            for val, prop in re.findall(r"<assign value='(.*?)' property='(.*?)' action='set' />", text)]
    return table(["Target", "Value"], rows, [4900, 4738])


TERMINAL_B3 = [
    'INSURLIGENT>set qbp=##class(EnsLib.HL7.Message).ImportFromString("MSH|^~\\&|D1_IRIS|D1|HIS|RAMA9|20261019120000||QBP^Q22^QBP_Q21|PAT0001|P|2.5.1"_$C(13)_"QPD|PAT-01^GetPatient^L|QPAT0001|3125800558898^^^TH^NI"_$C(13)_"RCP|I")',
    'INSURLIGENT>set sc=##class(EnsLib.Testing.Service).SendTestRequest("BO.HIS.HL7",qbp,.rsp,,1)',
    "INSURLIGENT>write sc",
    "1",
    "INSURLIGENT>write $Replace(rsp.OutputToString(),$Char(13),$Char(13,10))",
    "MSH|^~\\&|HIS|RAMA9|D1_IRIS|D1|20261019130935||RSP^K22^RSP_K21|RSPPAT0001|P|2.5.1",
    "MSA|AA|PAT0001",
    "QAK|QPAT0001|OK|PAT-01^GetPatient^L",
    "QPD|PAT-01^GetPatient^L|QPAT0001|3125800558898^^^TH^NI",
    "PID|1||HN00012345^^^RAMA9^MR~3125800558898^^^TH^NI||Jaidee^Somchai^^^Mr.||1990-05-15|M|||Bangkok^^^^^TH||081-234-5678",
]


def add_item(kind, cls, name):
    return [
        bullet(f"In the production page, click **+** next to **{kind}s**."),
        bullet(f"{kind} Class: `{cls}`. {kind} Name: `{name}`. Tick **Enable Now**. Click **OK**."),
    ]


def test_button(item, request_type, fields):
    return [
        bullet(f"In the production page, click `{item}`. In the panel on the right, open the **Actions** tab and click **Test**."),
        bullet(f"Request Type: `{request_type}`."),
        bullet(f"Fill in the fields: {fields}."),
        bullet("Click **Invoke Testing Service**."),
    ]


def lab_body(flow_png):
    b = [
        title("Interoperability Lab — Build a Production"),
        subtitle("DataOne / Insureligent Training · Interoperability · Lab handout"),
        p("In this lab you build a production, `Insurligent.Interop.Production`, in the `INSURLIGENT` namespace. It does a part of the pre-auth flow "
          "GetPreAuthInfo_View. It finds a patient in the hospital system with the HL7 query PAT-01. Then it finds the insured person "
          "at the insurer with the REST call Getinsurer."),
        p("You build it from right to left. First you build the business operations, which talk to the outside systems. Then you build the "
          "business processes, which control the order of the calls. Last you build the business service and the REST entry point. "
          "You test each part before you build the next part."),
        table(["Part", "What you do", "Time"], [
            ["A", "Create the production `Insurligent.Interop.Production`", "10 min"],
            ["B", "HL7 business operation `BO.HIS.HL7`, and test it", "20 min"],
            ["C", "REST business operation `BO.Insurer.REST` and its messages, and test it", "30 min"],
            ["D", "Sub-process `BP.HIS.Patient` with two DTLs, and test it", "45 min"],
            ["E", "Main process `BP.GetPreAuthInfoView`, and test it", "30 min"],
            ["F", "Business service, REST class, web application, end-to-end test", "30 min"],
        ], [1353, 6933, 1352]),
        p("Before you start:", after=60),
        bullet("You did the Environment Set-up Worksheet, and all its checks pass."),
        bullet("Your containers are running: `docker compose up -d`"),
        bullet("You can open the ObjectScript terminal: `docker compose exec iris iris session IRIS -U INSURLIGENT`"),
        bullet("VS Code connects to `INSURLIGENT`."),
        bullet("Login everywhere: username `_SYSTEM`, password `SYS`."),
        p("In the examples, `INSURLIGENT>` is the terminal prompt. It shows your namespace. Type only the text after the `>`."),

        h1("Words used in this lab"),
        table(["Word", "Meaning"], [
            ["Production", "A set of connected parts (items) that move messages between systems. It runs in one namespace."],
            ["Item", "One part of a production. It has a name, for example `BO.HIS.HL7`, and a class."],
            ["Business operation (BO)", "An item that sends a message to an outside system and gets the reply."],
            ["Business process (BP)", "An item that controls the order of the calls. You draw it in BPL."],
            ["Business service (BS)", "An item that brings a request into the production."],
            ["Message", "An object that goes from one item to another. A request class extends `Ens.Request`. A reply class extends `Ens.Response`."],
            ["DTL", "A data transformation: it copies data from one message into a different message."],
            ["Visual Trace", "A picture of all the messages of one request, in time order."],
        ], [2600, 7038]),

        h1("The flow you build"),
        p("The picture on the next page shows the flow. Left: the sequence diagram. Middle: the classes of each step. Right: the items of "
          "the production, in call order. The steps 2.1, 2.2 and so on run inside IRIS after diagram step 2."),
        p("The file is `docs/Lab_Sequence_Overview.svg`. Open it in a browser to zoom in."),
        "<!--SECT:portrait-->",
        image(flow_png, LANDSCAPE_W, "The lab flow: sequence diagram, classes, and the IRIS flow (docs/Lab_Sequence_Overview.svg)."),
        "<!--SECT:landscape-->",
        h2("The items you build, in this order"),
        table(["Order", "Production item", "Class", "Kind", "Part"], [
            ["1", "`BO.HIS.HL7`", "`EnsLib.HL7.Operation.TCPOperation` (built in)", "BO, HL7", "B"],
            ["2", "`BO.Insurer.REST`", "`Insurligent.Interop.BO.InsurerRest`", "BO, REST", "C"],
            ["3", "`BP.HIS.Patient`", "`Insurligent.Interop.BP.HISPatient`", "BP (sub-process)", "D"],
            ["4", "`BP.GetPreAuthInfoView`", "`Insurligent.Interop.BP.GetPreAuthInfoView`", "BP (main process)", "E"],
            ["5", "`BS.GetPreAuthInfoView`", "`Insurligent.Interop.BS.D1FrontService`", "BS", "F"],
            ["6", "(no item)", "`Insurligent.REST.Router`", "REST class, web application `/api/insurligent`", "F"],
        ], [800, 2000, 3500, 2538, 800]),
        p("Save each class in VS Code under `src/Insurligent`, in the folder of its package, for example "
          "`src/Insurligent/Interop/MSG/Insurer/GetInsurerRequest.cls`. The package folders are already there. When you save, "
          "VS Code compiles the class on the server. Check the Output view: there must be no errors."),
        p("You make the production, the DTLs and the BPLs in the Management Portal. They are on the server. To see them in VS Code, "
          "use the InterSystems Explorer view."),
        p("The finished classes are in `solution/src/Insurligent`. Use them only to check your work."),

        h1("Part A — Create the production"),
        h2("A1. Create the production"),
        bullet(f"Open the Management Portal: `{PORTAL}`"),
        bullet("Go to Interoperability. If IRIS asks for a namespace, choose `INSURLIGENT`. Then go to Configure › Production."),
        bullet("Click **New**. Package: `Insurligent.Interop`. Production Name: `Production`. Description: `Lab: GetPreAuthInfo_View with PAT-01 and Getinsurer`. Click **OK**."),
        bullet("IRIS creates the class `Insurligent.Interop.Production` and opens it. It has no items."),
        h2("A2. Turn on testing"),
        p("The Test button sends a test message to one item. It works only when the production allows it.", after=60),
        bullet("Click the production name at the top of the diagram. In the panel on the right, open the **Settings** tab."),
        bullet("Under Development and Debugging, tick **Testing Enabled**. Click **Apply**."),
        bullet("Click **Start**. The status changes to Running."),
        p("**Note:** only one production runs in a namespace at a time. In this lab, the namespace has only yours."),
        check("`Insurligent.Interop.Production` runs and has no items."),

        h1("Part B — HL7 business operation: BO.HIS.HL7"),
        p("This item sends HL7 messages to the hospital system and gets the reply. You do not write a class: IRIS has one, "
          "`EnsLib.HL7.Operation.TCPOperation`."),
        h2("B1. Add the operation"),
        *add_item("Operation", "EnsLib.HL7.Operation.TCPOperation", "BO.HIS.HL7"),
        h2("B2. Set the connection"),
        p("Click the new item. In the **Settings** tab, set these values, then click **Apply**:"),
        table(["Setting", "Value"], [["IP Address", "`mock_his`"], ["Port", "`2575`"]], [3800, 5838]),
        p("**Note:** use `mock_his`, not `localhost`. IRIS runs in its own container, and it finds the other containers by name."),
        h2("B3. Test it from the terminal"),
        p("It is easier to send an HL7 message from the terminal than from the Test button. Open the terminal:"),
        code(["docker compose exec iris iris session IRIS -U INSURLIGENT"]),
        p("Make a PAT-01 query, send it to the item, and show the reply. The first command is one line:"),
        code(TERMINAL_B3),
        p("`EnsLib.Testing.Service` is the same service that the Test button uses. `MSA|AA` means the HIS accepted the query. "
          "`QAK` shows `OK`: the HIS found the patient. The patient is in the `PID` segment."),
        h2("B4. Look at the Visual Trace"),
        bullet("Go to Interoperability › View › Messages."),
        bullet("Click the newest session, then **Visual Trace**."),
        bullet("You see two messages: the query from `EnsLib.Testing.Service` to `BO.HIS.HL7`, and the reply. Click each one to see its contents."),
        check("`BO.HIS.HL7` sends a PAT-01 query and gets a reply with the patient."),

        h1("Part C — REST business operation: BO.Insurer.REST"),
        p("This item calls the insurer API Getinsurer. IRIS has no class for this API, so you write one. You also write the messages that it uses."),
        h2("C1. The request message"),
        p("Create `src/Insurligent/Interop/MSG/Insurer/GetInsurerRequest.cls`. A request class extends `Ens.Request`. `[ Required ]` makes IRIS refuse a message without the field."),
        snippet("Interop/MSG/Insurer/GetInsurerRequest.cls"),
        h2("C2. The reply messages"),
        p("The insurer replies with JSON. `insured_person` is a JSON object inside the reply, so it gets its own class: a serial object. "
          "`%JSONFIELDNAME` gives the JSON name of each property. Create `src/Insurligent/Interop/MSG/Type/InsuredPersonInfo.cls`:"),
        snippet("Interop/MSG/Type/InsuredPersonInfo.cls"),
        p("Then create `src/Insurligent/Interop/MSG/Insurer/GetInsurerResponse.cls`:"),
        snippet("Interop/MSG/Insurer/GetInsurerResponse.cls"),
        p("**Note:** the insurer sends `insurer_age` as a number (`36`), so `Age` is an `%Integer`. With `%String`, `%JSONImport()` stops with an error."),
        h2("C3. The operation class"),
        p("Create `src/Insurligent/Interop/BO/InsurerRest.cls`:"),
        snippet("Interop/BO/InsurerRest.cls"),
        p("How it works:", after=60),
        bullet("`ADAPTER` connects the class to `EnsLib.HTTP.OutboundAdapter`. The adapter has the settings for the server: host, port and URL."),
        bullet("The `MessageMap` sends each type of request to one method. Here it has one entry: a `GetInsurerRequest` goes to `GetInsurer()`."),
        bullet("`GetInsurer()` makes the HTTP request, sends it with `SendFormDataArray()`, and reads the JSON reply into the reply message with `%JSONImport()`."),
        bullet("If the insurer does not know the person, it replies with HTTP 404 and a JSON body. The method still reads the body, so the caller gets `ResponseCode` 404 as data, not as an error."),
        h2("C4. Add the operation"),
        *add_item("Operation", "Insurligent.Interop.BO.InsurerRest", "BO.Insurer.REST"),
        p("In the **Settings** tab, set these values, then click **Apply**:"),
        table(["Setting", "Value"], [["HTTP Server", "`mock_insurer`"], ["HTTP Port", "`8080`"], ["URL", "`/api`"]], [3800, 5838]),
        h2("C5. Test it with the Test button"),
        *test_button("BO.Insurer.REST", "Insurligent.Interop.MSG.Insurer.GetInsurerRequest", "IdentityType `CID`, IdentityNo `3-1258-00558-89-8`, CompanyCode `AIA`"),
        p("The reply has `ResponseCode` 200, and an `InsuredPerson` with `InsurerId` INS123456, `FirstName` Somchai and `Age` 36. "
          "Click **Visual Trace** to see the request and the reply."),
        h2("C6. Test a person that the insurer does not know"),
        p("Send the test again with IdentityNo `9999999999999`. The reply has `ResponseCode` 404. The Visual Trace shows no error: here, 404 is data."),
        check("`BO.Insurer.REST` calls Getinsurer and gives back a `GetInsurerResponse`, for a known person and for an unknown person."),

        h1("Part D — Sub-process: BP.HIS.Patient"),
        p("This BP does one PAT-01 query. It gets a `PatientRequest` and makes the HL7 query with a DTL. It sends the query to `BO.HIS.HL7`. "
          "A second DTL makes a `PatientResponse` from the HL7 reply. Its caller never sees HL7."),
        h2("D1. The messages"),
        p("Create `src/Insurligent/Interop/MSG/HIS/PatientRequest.cls` and `src/Insurligent/Interop/MSG/HIS/PatientResponse.cls`:"),
        snippet("Interop/MSG/HIS/PatientRequest.cls"),
        snippet("Interop/MSG/HIS/PatientResponse.cls"),
        h2("D2. DTL 1: from PatientRequest to the HL7 query"),
        bullet("Go to Interoperability › Build › Data Transformations and click **New**."),
        bullet("Package: `Insurligent.Interop.DTL`. Name: `PatientToQBP`."),
        bullet("Source Class: `Insurligent.Interop.MSG.HIS.PatientRequest`. Target Class: `EnsLib.HL7.Message`. Target Document Type: `2.5.1:QBP_Q21`. Click **OK**."),
        p("Add one **Set** action for each line of this table. Drag a source property to a target property, or type the value:"),
        dtl_table("Interop/DTL/PatientToQBP.cls"),
        p("The CID has dashes in JSON but not in HL7, so `$Translate()` removes them. Save and compile. In VS Code, the class must look like this:"),
        snippet("Interop/DTL/PatientToQBP.cls"),
        h2("D3. DTL 2: from the HL7 reply to PatientResponse"),
        bullet("Create a new data transformation. Package: `Insurligent.Interop.DTL`. Name: `RSPToPatient`."),
        bullet("Source Class: `EnsLib.HL7.Message`. Source Document Type: `2.5.1:RSP_K22`. Target Class: `Insurligent.Interop.MSG.HIS.PatientResponse`. Click **OK**."),
        p("First add a **Code** action with this line:"),
        code(['Do source.PokeDocType("2.5.1:RSP_K22")']),
        p("The HL7 operation does not set the document type of a reply. Without it, the paths below find nothing. Then add the **Set** actions:"),
        dtl_table("Interop/DTL/RSPToPatient.cls"),
        p("In the reply structure RSP_K22, the PID segment is inside the group `PIDgrp`, so the paths start with `PIDgrp(1).PID`. "
          "Save and compile, and compare with:"),
        snippet("Interop/DTL/RSPToPatient.cls"),
        h2("D4. The BPL"),
        bullet("Go to Interoperability › Build › Business Processes and click **New**."),
        bullet("Package: `Insurligent.Interop.BP`. Name: `HISPatient`. Request Class: `Insurligent.Interop.MSG.HIS.PatientRequest`. Response Class: `Insurligent.Interop.MSG.HIS.PatientResponse`."),
        bullet("In the **Context** tab, add two properties, `QBP` and `RSP`, both of type `EnsLib.HL7.Message`."),
        bullet("Add these activities, in this order:"),
        table(["Activity", "Name", "Settings"], [
            ["Transform", "Build QBP", "Class `Insurligent.Interop.DTL.PatientToQBP`. Source `request`. Target `context.QBP`."],
            ["Call", "Send PAT-01", "Target `BO.HIS.HL7`. Asynchronous: not ticked. Request type `EnsLib.HL7.Message`: set `callrequest` to `context.QBP`. "
                                    "Response type `EnsLib.HL7.Message`: set `context.RSP` to `callresponse`."],
            ["Transform", "Read RSP", "Class `Insurligent.Interop.DTL.RSPToPatient`. Source `context.RSP`. Target `response`."],
        ], [1400, 1800, 6438]),
        p("Save and compile. Compare with:"),
        snippet("Interop/BP/HISPatient.cls"),
        h2("D5. Add the process"),
        *add_item("Business Process", "Insurligent.Interop.BP.HISPatient", "BP.HIS.Patient"),
        h2("D6. Test it"),
        *test_button("BP.HIS.Patient", "Insurligent.Interop.MSG.HIS.PatientRequest", "IdentityNo `3-1258-00558-89-8`, HospitalCode `RAMA9`"),
        p("The reply has `ResponseCode` 200, `HospitalNumber` HN00012345, `FirstName` Somchai, `LastName` Jaidee, `BirthDate` 1990-05-15 "
          "and `Gender` M. The Visual Trace shows that the BP calls `BO.HIS.HL7`."),
        p("Test again with IdentityNo `9999999999999`. The reply has `ResponseCode` 404 and the message \"Patient not found in the HIS\"."),
        check("`BP.HIS.Patient` turns a `PatientRequest` into a `PatientResponse`, and its caller sees no HL7."),

        h1("Part E — Main process: BP.GetPreAuthInfoView"),
        p("This BP is the flow of GetPreAuthInfo_View. It calls the sub-process of Part D. If the HIS finds the patient, it calls the REST operation of Part C."),
        h2("E1. The messages"),
        p("Create `src/Insurligent/Interop/MSG/PreAuth/View/GetPreAuthInfoViewRequest.cls`. `VALUELIST` allows only CID, and `[ Required ]` refuses a request without the field. "
          "IRIS checks both when it imports the JSON."),
        snippet("Interop/MSG/PreAuth/View/GetPreAuthInfoViewRequest.cls"),
        p("Create `src/Insurligent/Interop/MSG/PreAuth/View/GetPreAuthInfoViewResponse.cls`:"),
        snippet("Interop/MSG/PreAuth/View/GetPreAuthInfoViewResponse.cls"),
        h2("E2. The BPL"),
        bullet("Create a new business process. Package: `Insurligent.Interop.BP`. Name: `GetPreAuthInfoView`. Request Class: `Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest`. Response Class: `Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewResponse`."),
        bullet("It needs no context properties. Add these activities:"),
        table(["Activity", "Name", "Settings"], [
            ["Call", "Get patient (PAT-01)", "Target `BP.HIS.Patient`. Request `Insurligent.Interop.MSG.HIS.PatientRequest`: set `IdentityNo` and `HospitalCode` from `request`. "
                                             "Response `Insurligent.Interop.MSG.HIS.PatientResponse`: copy `ResponseCode`, `ResponseMessage`, `HospitalNumber`, `FirstName`, `LastName`, `BirthDate` and `Gender` from `callresponse` to `response`."],
            ["If", "Patient found?", "Condition `response.ResponseCode=\"200\"`."],
            ["Call (in the true branch)", "Getinsurer", "Target `BO.Insurer.REST`. Request `Insurligent.Interop.MSG.Insurer.GetInsurerRequest`: `IdentityType` = `\"CID\"`, `IdentityNo` from `request`, `CompanyCode` = `\"AIA\"`. "
                                                    "Response: set `response.InsurerId` from `callresponse.InsuredPerson.InsurerId`, and `response.CompanyCode`."],
        ], [1700, 1900, 6038]),
        p("Save and compile. Compare with:"),
        snippet("Interop/BP/GetPreAuthInfoView.cls"),
        p("**Note:** the spec gives no list of insurer companies (spec defect SD-03), so the training flow asks one insurer, AIA."),
        h2("E3. Add the process"),
        *add_item("Business Process", "Insurligent.Interop.BP.GetPreAuthInfoView", "BP.GetPreAuthInfoView"),
        h2("E4. Test it"),
        *test_button("BP.GetPreAuthInfoView", "Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest", "SearchType `CID`, IdentityNo `3-1258-00558-89-8`, HospitalCode `RAMA9`"),
        p("The reply has `ResponseCode` 200, the patient Somchai Jaidee, `InsurerId` INS123456 and `CompanyCode` AIA. The Visual Trace shows "
          "the BP call `BP.HIS.Patient` (which calls `BO.HIS.HL7`), then `BO.Insurer.REST`."),
        p("Test again with IdentityNo `9999999999999`. The reply has `ResponseCode` 404, and the Visual Trace shows no call to `BO.Insurer.REST`."),
        check("`BP.GetPreAuthInfoView` calls a BP and a BO, and uses an `if` to decide on the second call."),

        h1("Part F — Business service, REST and end to end"),
        h2("F1. The business service"),
        p("Create `src/Insurligent/Interop/BS/D1FrontService.cls`. The business service has no adapter: the REST class calls it. `SendRequestSync()` sends "
          "the request to the BP in `TargetConfigName` and waits up to 60 seconds for the reply."),
        snippet("Interop/BS/D1FrontService.cls"),
        h2("F2. Add the service"),
        *add_item("Service", "Insurligent.Interop.BS.D1FrontService", "BS.GetPreAuthInfoView"),
        p("In the **Settings** tab, set these values, then click **Apply**:"),
        table(["Setting", "Value"], [["Pool Size", "`0` (the REST class starts the service, so it needs no job of its own)"],
                                     ["Target Config Name", "`BP.GetPreAuthInfoView`"]], [3800, 5838]),
        h2("F3. The REST class"),
        p("Create `src/Insurligent/REST/Router.cls`:"),
        snippet("REST/Router.cls"),
        p("How it works:", after=60),
        bullet("The `UrlMap` sends `POST /preauth/info` to the method `PreAuthInfo()`."),
        bullet("`%JSONImport()` and `%ValidateObject()` check the request against the rules of the class. A wrong request gets HTTP 400."),
        bullet("`CreateBusinessService()` and `ProcessInput()` send the request into the production through `BS.GetPreAuthInfoView`."),
        bullet("`%JSONExport()` writes the reply as JSON."),
        h2("F4. Create the web application"),
        bullet("Go to System Administration › Security › Applications › Web Applications. Click **Create New Web Application**."),
        bullet("Use these settings, then click **Save**:"),
        table(["Setting", "Value"], [["Name", "`/api/insurligent`"], ["Namespace", "`INSURLIGENT`"], ["Enable Application", "ticked"], ["Enable", "REST"],
                                     ["Dispatch Class", "`Insurligent.REST.Router`"], ["Allowed Authentication Methods", "Password only"]], [3800, 5838]),
        h2("F5. Test from end to end"),
        p("Use your REST client. For every request, use Basic authentication (`_SYSTEM` / `SYS`) and the header `Content-Type: application/json`."),
        p("**1. A known patient.** `POST http://localhost:52773/api/insurligent/preauth/info` with this body:"),
        code(CID_BODY),
        p("You should get:"),
        code(['{"response_code":"200","response_message":"Success","hospital_number":"HN00012345","first_name":"Somchai","last_name":"Jaidee",'
              '"birth_date":"1990-05-15","gender":"M","insurer_id":"INS123456","company_code":"AIA"}']),
        p('**2. A passport search.** Change `search_type` to `"PID"`. You should get HTTP 400:'),
        code(['{"response_code":"400","response_message":"ERROR #9406: Unexpected format for value of field, search_type, using class base mapping"}']),
        p("**3. A missing field.** Remove `identity_no`. You should get HTTP 400:"),
        code(['{"response_code":"400","response_message":"ERROR #9405: Required field not present, identity_no, using class base mapping"}']),
        p('**4. An unknown patient.** Use `"identity_no": "9999999999999"`. You should get:'),
        code(['{"response_code":"404","response_message":"Patient not found in the HIS"}']),
        h2("F6. Look at the whole flow"),
        p("Open the Visual Trace of request 1 (Interoperability › View › Messages, newest session). It starts at `BS.GetPreAuthInfoView` and shows "
          "every call: `BP.GetPreAuthInfoView`, `BP.HIS.Patient`, `BO.HIS.HL7`, then `BO.Insurer.REST`. Compare it with the right column of the flow picture: steps 1 to 5."),
        check("the REST request goes through the BS, the two BPs and the two BOs, and you can follow it in the Visual Trace."),

        h1("If something goes wrong"),
        table(["Problem", "What to do"], [
            ["The Test button is not there, or it is grey", "The production must run, **Testing Enabled** must be ticked (A2), and the item must be enabled."],
            ["`BO.HIS.HL7` or `BO.Insurer.REST` cannot connect", "Check the settings. `BO.HIS.HL7`: `mock_his`, `2575`. `BO.Insurer.REST`: `mock_insurer`, `8080`, `/api`. Check that the mocks run: `docker compose ps`."],
            ["A class does not compile", "Read the Output view in VS Code. Compare your class with `solution/src/Insurligent`."],
            ["The reply has `ResponseCode` 200 but no patient fields", "In DTL 2, check the Code action with `PokeDocType`, and the paths that start with `PIDgrp(1).PID`."],
            ["HTTP 401 from `/api/insurligent`", "Use Basic authentication `_SYSTEM` / `SYS`. Check that the web application allows Password."],
            ["HTTP 500 that names `BS.GetPreAuthInfoView`", "`Insurligent.Interop.Production` must run, and the item must be enabled with exactly the name `BS.GetPreAuthInfoView`."],
            ["You changed a BP or BO class, but it acts as before", "Running items keep the old code. Click **Update** in the production page, or stop and start the production."],
        ], [3800, 5838]),

        h1("Checklist"),
        table(["Done", "Check"], [
            ["☐", "`BO.HIS.HL7` answers a PAT-01 query from the terminal (B3)."],
            ["☐", "`BO.Insurer.REST` gives 200 for a known person and 404 for an unknown person (C5, C6)."],
            ["☐", "`BP.HIS.Patient` gives the patient from a `PatientRequest` (D6)."],
            ["☐", "`BP.GetPreAuthInfoView` gives the patient and the insurer, and skips Getinsurer for an unknown patient (E4)."],
            ["☐", "`POST /api/insurligent/preauth/info` gives the four results of F5."],
            ["☐", "I can follow one request in the Visual Trace from `BS.GetPreAuthInfoView` to both BOs (F6)."],
        ], [900, 8738]),
    ]
    return "".join(b)

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        sys_svg, sys_png = os.path.join(tmp, "systems.svg"), os.path.join(tmp, "systems.png")
        systems_svg(sys_svg)
        svg_to_png(sys_svg, sys_png)
        flow_png = os.path.join(tmp, "flow.png")
        svg_to_png(os.path.join(ROOT, "docs", "Lab_Sequence_Overview.svg"), flow_png)

        IMAGES.clear()
        build(os.path.join(REF, "Environment_Setup_Worksheet.docx"), os.path.join(ROOT, "docs", "Environment_Setup_Worksheet.docx"),
              "Environment Set-up Worksheet – Interoperability lab", environment_body(sys_png), "Environment Set-up Worksheet")
        IMAGES.clear()
        build(os.path.join(REF, "Day1_Lab_Handout 1.docx"), os.path.join(ROOT, "docs", "Lab_Handout.docx"),
              "Interoperability Lab – Build a Production", lab_body(flow_png), "Interoperability Lab")
