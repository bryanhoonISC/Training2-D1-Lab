#!/usr/bin/env bash
# Instructor: load the answer key (solution/src) into INSURLIGENT, create the web
# application /api/insurligent, and start Insurligent.Interop.Production.
# It replaces the classes of the same names. Run it in the lab folder: solution/load.sh
set -euo pipefail
cd "$(dirname "$0")/.."
iris() { docker compose exec -T iris iris session IRIS -U INSURLIGENT; }

docker compose exec -T -u root iris rm -rf /tmp/lab-solution
docker compose cp solution/src iris:/tmp/lab-solution > /dev/null 2>&1
iris <<'EOF' | grep "\[solution\]"
set sc=$SYSTEM.OBJ.LoadDir("/tmp/lab-solution","ck-d",,1) write !,"[solution] classes loaded: ",$System.Status.IsOK(sc)," ",$System.Status.GetErrorText(sc),!
zn "%SYS"
if '##class(Security.Applications).Exists("/api/insurligent") { set p("NameSpace")="INSURLIGENT",p("DispatchClass")="Insurligent.REST.Router",p("Enabled")=1,p("AutheEnabled")=32,p("Description")="Lab: GetPreAuthInfo_View" set sc=##class(Security.Applications).Create("/api/insurligent",.p) write !,"[solution] web application /api/insurligent created: ",$System.Status.IsOK(sc),! }
zn "INSURLIGENT"
do ##class(Ens.Director).StopProduction(10,1)
set sc=##class(Ens.Director).StartProduction("Insurligent.Interop.Production") write !,"[solution] Insurligent.Interop.Production started: ",$System.Status.IsOK(sc),!
halt
EOF
