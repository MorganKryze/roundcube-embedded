import requests
from flask import Flask, Response, request
import re
from urllib.parse import urlparse, urljoin

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

    # Build cookies string from browser cookies
    cookie_header = "; ".join([f"{k}={v}" for k, v in request.cookies.items()])
    if cookie_header:
        headers["Cookie"] = cookie_header

    resp = requests.request(
        method,
        url,
        headers=headers,
        data=data,
        allow_redirects=False,  # Back to False
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
        "location",  # We'll handle this separately
    ]

    response_headers = [
        (name, value)
        for (name, value) in resp.raw.headers.items()
        if name.lower() not in excluded_headers
    ]

    # Handle redirects - rewrite Location header
    if resp.status_code in [301, 302, 303, 307, 308]:
        location = resp.headers.get("Location", "")
        if location:
            # Convert absolute URLs to relative proxy URLs
            if location.startswith("http"):
                parsed = urlparse(location)
                new_location = parsed.path
                if parsed.query:
                    new_location += "?" + parsed.query
                response_headers.append(("Location", new_location))
            else:
                response_headers.append(("Location", location))

    # Add permissive headers
    response_headers.append(("X-Frame-Options", "ALLOWALL"))
    response_headers.append(("Content-Security-Policy", "frame-ancestors *"))

    # Pass through Set-Cookie headers exactly as received
    for header_name, header_value in resp.raw.headers.items():
        if header_name.lower() == "set-cookie":
            # Remove Secure and SameSite=None to work in iframe
            cookie_value = header_value
            cookie_value = re.sub(r";\s*Secure", "", cookie_value, flags=re.IGNORECASE)
            cookie_value = re.sub(
                r";\s*SameSite=\w+", "", cookie_value, flags=re.IGNORECASE
            )
            cookie_value = re.sub(
                r";\s*Domain=[^;]+", "", cookie_value, flags=re.IGNORECASE
            )
            response_headers.append(("Set-Cookie", cookie_value))

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
            rb"(?:top|parent)\.location\s*=",
            b"window.location =",
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
