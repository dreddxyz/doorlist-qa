"""Run three independent suites, preserve diagnostics and publish a release receipt."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from prefect import flow, task

@task
def suite(name, file):
    Path("reports").mkdir(exist_ok=True)
    target=Path("reports")/(name+".xml")
    result=subprocess.run([sys.executable,"-m","pytest","-q",file,"--junitxml",str(target)])
    cases=[]
    if target.exists():
        for case in ET.parse(target).iter("testcase"):
            outcome=next((s for s in ("failure","error","skipped") if case.find(s) is not None),"pass")
            cases.append({"name":case.get("name"),"seconds":float(case.get("time","0")),"outcome":outcome})
    return {"suite":name,"ok":result.returncode==0 and bool(cases) and all(c["outcome"]=="pass" for c in cases),"cases":cases}

@flow(name="doorlist-release")
def main():
    groups=[suite(n,f) for n,f in [("API","test_api.py"),("Chromium","test_chromium.py"),("Firefox","test_firefox.py")]]
    report={"suites":groups,"ok":all(g["ok"] for g in groups),"sha":os.getenv("GITHUB_SHA","local"),
            "run":os.getenv("GITHUB_RUN_ID",""),"at":datetime.now(timezone.utc).isoformat()}
    Path("site/receipt.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report["ok"]

if __name__=="__main__":
    sys.exit(0 if main() else 1)
