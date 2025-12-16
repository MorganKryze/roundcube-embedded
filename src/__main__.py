import requests
from flask import Flask, Response, request
import re

app = Flask(__name__)
TARGET_URL = "https://mail.ovh.net/roundcube/"


@app.route(
    "/",
    defaults={"path": ""},
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
@app.route(
    "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
)
def proxy(path):
    url = TARGET_URL + path
    if request.query_string:
        url += "?" + request.query_string.decode()

    headers = {
        key: value
        for key, value in request.headers
        if key.lower() not in ["host", "origin", "referer"]
    }
    headers["Host"] = "mail.ovh.net"

    method = request.method
    data = request.get_data() if method in ["POST", "PUT", "PATCH"] else None

    # Follow redirects server-side
    resp = requests.request(
        method,
        url,
        headers=headers,
        data=data,
        cookies=request.cookies,
        allow_redirects=True,  # Changed to True
        stream=True,
        verify=True,
    )

    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
        "x-frame-options",
        "content-security-policy",
        "content-security-policy-report-only",
        "frame-options",
        "strict-transport-security",
    ]

    response_headers = [
        (name, value)
        for (name, value) in resp.raw.headers.items()
        if name.lower() not in excluded_headers
    ]

    # Add permissive headers
    response_headers.append(("X-Frame-Options", "ALLOWALL"))
    response_headers.append(("Content-Security-Policy", "frame-ancestors *"))

    # Fix cookies - preserve session cookies
    for cookie in resp.cookies:
        cookie_str = f"{cookie.name}={cookie.value}; Path=/"
        if cookie.name.lower() in ["sessid", "roundcube_sessid", "session"]:
            cookie_str += "; HttpOnly"
        response_headers.append(("Set-Cookie", cookie_str))

    # Check if response is HTML and remove frame-busting
    content_type = resp.headers.get("Content-Type", "")
    if "text/html" in content_type:
        content = b"".join(resp.iter_content(chunk_size=8192))

        # Remove frame-busting meta tags
        content = re.sub(
            rb'<meta[^>]*http-equiv=["\']?X-Frame-Options["\']?[^>]*>',
            b"",
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            rb'<meta[^>]*http-equiv=["\']?Content-Security-Policy["\']?[^>]*>',
            b"",
            content,
            flags=re.IGNORECASE,
        )

        # Remove common frame-busting JavaScript patterns
        content = re.sub(
            rb"if\s*\(\s*(?:window\s*\.?\s*top|top)\s*!==?\s*(?:window\s*\.?\s*self|self)\s*\)[^}]*\{[^}]*\}",
            b"",
            content,
            flags=re.IGNORECASE,
        )

        # Remove top.location redirects
        content = re.sub(
            rb'(?:top|parent)\.location\s*=\s*["\'][^"\']*["\']',
            b"window.location = window.location",
            content,
            flags=re.IGNORECASE,
        )

        # Remove window.top checks
        content = re.sub(
            rb"if\s*\(\s*window\s*!=\s*top\s*\)",
            b"if (false)",
            content,
            flags=re.IGNORECASE,
        )

        return Response(content, resp.status_code, response_headers)
    else:

        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                yield chunk

        return Response(generate(), resp.status_code, response_headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=True)
