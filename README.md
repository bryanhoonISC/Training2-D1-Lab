# Training2-D1-Lab

A hands-on lab for InterSystems IRIS interoperability. Students build a small production in the `INSURLIGENT` namespace. The production does one part of the D1 pre-auth flow `GetPreAuthInfo_View`, with a citizen ID (CID) search only:

1. It finds the patient in the hospital system (HIS) with the HL7 query PAT-01.
2. It finds the insured person at the insurer (company AIA) with the REST call Getinsurer.

Students build the production from right to left, and test each part before they build the next one:

| Part | What students build | Test |
|---|---|---|
| A | The production `Insurligent.Interop.Production` | — |
| B | HL7 business operation `BO.HIS.HL7` | BO |
| C | REST business operation `BO.Insurer.REST` (one MessageMap entry) and its messages | BO |
| D | Sub-process `BP.HIS.Patient` with two DTLs | BP |
| E | Main process `BP.GetPreAuthInfoView`, which calls the sub-process | BP |
| F | Business service `BS.GetPreAuthInfoView`, REST class, web application `/api/insurligent` | End to end |

## Students

Do these two documents in this order:

1. [docs/Environment_Setup_Worksheet.docx](docs/Environment_Setup_Worksheet.docx): before the lab. It installs and checks the environment.
2. [docs/Lab_Handout.docx](docs/Lab_Handout.docx): during the lab. It gives each step, the code and the expected result.

[docs/Lab_Sequence_Overview.svg](docs/Lab_Sequence_Overview.svg) shows the flow: the sequence diagram, the classes of each step, and the production items in call order. Open it in a browser to zoom in.

Quick start (Docker Desktop, or Docker with Compose v2):

```bash
git clone https://github.com/bryanhoonISC/Training2-D1-Lab.git
cd Training2-D1-Lab
docker compose up -d --build
docker compose logs -f iris     # wait for: [insurligent-setup] complete.
```

## The systems

| Container | What it is | Port on your computer |
|---|---|---|
| `iris` | IRIS for Health Community, namespace `INSURLIGENT` | 52773 (web, Management Portal, REST), 9091 (superserver) |
| `mock_his` | Test hospital system. Answers HL7 v2.5.1 queries over MLLP. | 2575 |
| `mock_insurer` | Test insurer. Answers REST calls with JSON. | 8080 |

All ports are on `127.0.0.1` only. Login: `_SYSTEM` / `SYS`.

Management Portal: <http://localhost:52773/csp/sys/UtilHome.csp>

Inside Docker, IRIS connects to `mock_his:2575` and `mock_insurer:8080`.

## Folders

| Folder | Contents |
|---|---|
| `src/Insurligent/` | Empty package folders. Students put their classes here. VS Code (`.vscode/settings.json`) connects to `INSURLIGENT`. |
| `setup/` | The first-start set-up: loads the classes in `src/`. It makes no production. |
| `merge.cpf` | Makes the `INSURLIGENT` database and namespace, with interoperability enabled. |
| `mock_his/`, `mock_insurer/` | The two test systems and their data. |
| `solution/` | The answer key, for instructors. IRIS does not load it. |
| `docs/` | The worksheet, the handout and the overview diagram. |
| `docs/tools/` | The scripts that make the diagram and the handouts. |
| `data/durable/` | IRIS data (not in git). It keeps the namespace and the student work across restarts. |

## Instructors

Load the answer key into a running environment, then check it:

```bash
solution/load.sh     # loads solution/src, makes /api/insurligent, starts the production
solution/smoke.sh    # 15 checks: each BO, each BP, then end to end
```

`load.sh` replaces the student classes that have the same names. Use it on an instructor copy, or after the lab.

To go back to a clean environment, stop the containers and delete `data/durable/iris_conf.d`:

```bash
docker compose down
rm -rf data/durable/iris_conf.d
docker compose up -d
```

## Make the documents again

Edit the scripts in `docs/tools/`, then run them from the repository folder:

```bash
python3 -I docs/tools/gen_overview_svg.py   # docs/Lab_Sequence_Overview.svg
python3 -I docs/tools/build_handouts.py     # the two .docx files
```

`build_handouts.py` needs:

- The reference documents `Environment_Setup_Worksheet.docx` and `Day1_Lab_Handout 1.docx` in `docs/reference/`. They give the styles, the header and the footer. They are not in git: get them from the course owner.
- Google Chrome, to change the SVG diagrams to PNG. Set `CHROME` if Chrome is not in `/Applications`.

The handouts copy the code from `solution/src/`, so they always show the tested answer key.
