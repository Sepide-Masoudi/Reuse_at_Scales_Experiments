#!/usr/bin/env python3
"""
featurecounts_service.py
Persistent HTTP service wrapping featureCounts tool.
Accepts BAM files and annotation paths from shared PVC,
runs featureCounts, returns output file paths.
"""

import os
import subprocess
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("featurecounts-service")

# Thread lock to serialize requests if needed
lock = threading.Lock()


class FeatureCountsHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log.info(format % args)

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            self._respond(200, {"status": "ok", "service": "featurecounts"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/run":
            self._respond(404, {"error": "not found"})
            return

        # Parse request body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            req = json.loads(body)
        except Exception as e:
            self._respond(400, {"error": f"invalid JSON: {e}"})
            return

        # Required fields
        bams        = req.get("bams")        # list of BAM file paths on PVC
        annotation  = req.get("annotation")  # GTF/GFF annotation path on PVC
        outdir      = req.get("outdir")      # output directory path on PVC
        prefix      = req.get("prefix")      # output file prefix
        paired_end  = req.get("paired_end", True)
        strandedness = req.get("strandedness", 0)
        cpus        = req.get("cpus", 2)
        args        = req.get("args", "")

        if not all([bams, annotation, outdir, prefix]):
            self._respond(400, {"error": "missing required fields: bams, annotation, outdir, prefix"})
            return

        os.makedirs(outdir, exist_ok=True)
        output_file = os.path.join(outdir, f"{prefix}.featureCounts.tsv")
        summary_file = f"{output_file}.summary"

        paired_flag = "-p" if paired_end else ""

        cmd = [
            "featureCounts",
            *args.split(),
            paired_flag,
            "-T", str(cpus),
            "-a", annotation,
            "-s", str(strandedness),
            "-o", output_file,
            *bams
        ]
        # Remove empty strings from cmd
        cmd = [c for c in cmd if c]

        log.info(f"Running featureCounts for {prefix}: {' '.join(cmd)}")

        with lock:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600
                )
            except subprocess.TimeoutExpired:
                self._respond(500, {"error": "featureCounts timed out"})
                return
            except Exception as e:
                self._respond(500, {"error": str(e)})
                return

        if result.returncode != 0:
            log.error(f"featureCounts failed: {result.stderr}")
            self._respond(500, {
                "error": "featureCounts failed",
                "stderr": result.stderr,
                "stdout": result.stdout,
                "returncode": result.returncode
            })
            return

        log.info(f"featureCounts completed for {prefix}")
        self._respond(200, {
            "status": "success",
            "prefix": prefix,
            "counts": output_file,
            "summary": summary_file,
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
    port = int(os.environ.get("SERVICE_PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), FeatureCountsHandler)
    log.info(f"featureCounts service listening on port {port}")
    server.serve_forever()