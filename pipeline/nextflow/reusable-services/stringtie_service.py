#!/usr/bin/env python3
"""
stringtie_service.py
Persistent HTTP service wrapping StringTie tool.
Accepts BAM files and annotation paths from shared PVC,
runs StringTie, returns output file paths.
"""

import os
import subprocess
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("stringtie-service")

lock = threading.Lock()


class StringTieHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log.info(format % args)

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            self._respond(200, {"status": "ok", "service": "stringtie"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/run":
            self._respond(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            req = json.loads(body)
        except Exception as e:
            self._respond(400, {"error": f"invalid JSON: {e}"})
            return

        # Required fields
        bam          = req.get("bam")           # BAM file path on PVC
        annotation   = req.get("annotation")    # GTF annotation path on PVC
        outdir       = req.get("outdir")         # output directory on PVC
        prefix       = req.get("prefix")         # output prefix
        strandedness = req.get("strandedness", "unstranded")  # forward/reverse/unstranded
        cpus         = req.get("cpus", 2)
        args         = req.get("args", "")

        if not all([bam, outdir, prefix]):
            self._respond(400, {"error": "missing required fields: bam, outdir, prefix"})
            return

        os.makedirs(outdir, exist_ok=True)

        transcript_gtf = os.path.join(outdir, f"{prefix}.transcripts.gtf")
        abundance_txt  = os.path.join(outdir, f"{prefix}.gene.abundance.txt")
        coverage_gtf   = os.path.join(outdir, f"{prefix}.coverage.gtf")
        ballgown_dir   = os.path.join(outdir, f"{prefix}.ballgown")

        strand_flag = ""
        if strandedness == "forward":
            strand_flag = "--fr"
        elif strandedness == "reverse":
            strand_flag = "--rf"

        reference_flags = []
        if annotation:
            reference_flags = ["-G", annotation, "-b", ballgown_dir, "-C", coverage_gtf]

        cmd = [
            "stringtie",
            bam,
            *strand_flag.split(),
            *reference_flags,
            "-o", transcript_gtf,
            "-A", abundance_txt,
            "-p", str(cpus),
            *args.split()
        ]
        cmd = [c for c in cmd if c]

        log.info(f"Running StringTie for {prefix}: {' '.join(cmd)}")

        with lock:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600
                )
            except subprocess.TimeoutExpired:
                self._respond(500, {"error": "StringTie timed out"})
                return
            except Exception as e:
                self._respond(500, {"error": str(e)})
                return

        if result.returncode != 0:
            log.error(f"StringTie failed: {result.stderr}")
            self._respond(500, {
                "error": "StringTie failed",
                "stderr": result.stderr,
                "stdout": result.stdout,
                "returncode": result.returncode
            })
            return

        log.info(f"StringTie completed for {prefix}")
        self._respond(200, {
            "status": "success",
            "prefix": prefix,
            "transcript_gtf": transcript_gtf,
            "abundance": abundance_txt,
            "coverage_gtf": coverage_gtf if annotation else None,
            "ballgown": ballgown_dir if annotation else None,
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("SERVICE_PORT", 8081))
    server = HTTPServer(("0.0.0.0", port), StringTieHandler)
    log.info(f"StringTie service listening on port {port}")
    server.serve_forever()