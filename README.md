# Training2-D1-Lab

A hands-on lab for InterSystems IRIS interoperability. You build a small production in the `INSURLIGENT` namespace. The production does one part of the D1 pre-auth flow `GetPreAuthInfo_View`, with a citizen ID (CID) search only:

1. It finds the patient in the hospital system (HIS) with the HL7 query PAT-01.
2. It finds the insured person at the insurer (company AIA) with the REST call Getinsurer.

You build the production from right to left, and test each part before you build the next one:

| Part | What you build | Test |
|---|---|---|
| A | The production `Insurligent.Interop.Production` | — |
| B | HL7 business operation `BO.HIS.HL7` | BO |
| C | REST business operation `BO.Insurer.REST` (one MessageMap entry) and its messages | BO |
| D | Sub-process `BP.HIS.Patient` with two DTLs | BP |
| E | Main process `BP.GetPreAuthInfoView`, which calls the sub-process | BP |
| F | Business service `BS.GetPreAuthInfoView`, REST class, web application `/api/insurligent` | End to end |
| G | Task `Insurligent.Task.SFTPCleanup`: the Task Manager deletes old files on the SFTP server of the HIS | Task |

## Start here

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
| `mock_his` | Test hospital system. Answers HL7 v2.5.1 queries over MLLP. Has an SFTP server with test files for Part G. | 2575 (SFTP: only inside Docker) |
| `mock_insurer` | Test insurer. Answers REST calls with JSON. | 8080 |

All ports are on `127.0.0.1` only. Login: `_SYSTEM` / `SYS`.

Management Portal: <http://localhost:52773/csp/sys/UtilHome.csp>

Inside Docker, IRIS connects to `mock_his:2575`, `his-sftp:22` and `mock_insurer:8080`.

## Folders

| Folder | Contents |
|---|---|
| `src/Insurligent/` | Empty package folders. You put your classes here. VS Code (`.vscode/settings.json`) connects to `INSURLIGENT`. |
| `setup/` | The first-start set-up: loads the classes in `src/`, and deletes the Foundation production that IRIS makes. |
| `merge.cpf` | Makes the `INSURLIGENT` database and namespace, with interoperability enabled. |
| `mock_his/`, `mock_insurer/` | The two test systems and their data. |
| `solution/src/` | The finished classes. Use them only to check your work. IRIS does not load them. |
| `docs/` | The worksheet, the handout and the overview diagram. |
| `data/durable/` | IRIS data (not in git). It keeps the namespace and your work across restarts. |
