#!/usr/bin/env python3
"""serve_hub.py — serve dist/ so every artifact is a FORCED DOWNLOAD (MUST #16).

`http.server` alone opens artifacts in the browser's viewer on many Android clients; a
`.apk` served as `application/vnd.android.package-archive` may preview instead of saving.
MUST #16 requires the tap to DOWNLOAD. So every response carries
`Content-Disposition: attachment`, and `index.html` is served inline so the hub itself
still renders as the one surface.

Usage:  python3 tools/serve_hub.py [port] [dist_dir]
"""
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

INLINE = {"/", "/index.html"}


class ForcedDownload(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path in INLINE:
            self.send_header("Content-Disposition", "inline")
        else:
            name = os.path.basename(path) or "download"
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("serve_hub: " + fmt % args + "\n")


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 12001
    dist = sys.argv[2] if len(sys.argv) > 2 else "dist"
    handler = partial(ForcedDownload, directory=dist)
    srv = ThreadingHTTPServer(("0.0.0.0", port), handler)
    print(f"serve_hub: http://0.0.0.0:{port}/  (dist={dist}; every artifact forced as attachment)")
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
