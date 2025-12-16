import requests
from flask import Flask, Response, request
from urllib.parse import urljoin

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

    # Forward headers but modify Host
    headers = {
        key: value
        for key, value in request.headers
        if key.lower() not in ["host", "origin", "referer"]
    }
    headers["Host"] = "mail.ovh.net"

    method = request.method
    data = request.get_data() if method in ["POST", "PUT", "PATCH"] else None

    resp = requests.request(
        method,
        url,
        headers=headers,
        data=data,
        cookies=request.cookies,
        allow_redirects=False,
        stream=True,
        verify=True,
    )

    # Remove problematic headers
    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
        "x-frame-options",
        "content-security-policy",
        "frame-options",
        "strict-transport-security",
    ]

    response_headers = [
        (name, value)
        for (name, value) in resp.raw.headers.items()
        if name.lower() not in excluded_headers
    ]

    # Fix cookies - remove Domain, Secure, SameSite=None
    for cookie in resp.cookies:
        cookie_str = f"{cookie.name}={cookie.value}; Path=/"
        response_headers.append(("Set-Cookie", cookie_str))

    # Stream response
    def generate():
        for chunk in resp.iter_content(chunk_size=8192):
            yield chunk

    return Response(generate(), resp.status_code, response_headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=True)
