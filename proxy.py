"""
A simple proxy server. Usage:

http://hostname:port/p/(URL to be proxied, minus protocol)

For example:

http://localhost:8080/p/www.google.com

"""
from flask import Flask, render_template, request, abort, redirect, make_response, jsonify
import requests
import logging

app = Flask(__name__.split('.')[0])
logging.basicConfig(level=logging.INFO)
CHUNK_SIZE = 1024
LOG = logging.getLogger("main.py")


@app.route('/<path:url>', methods=['GET', 'POST', 'OPTIONS'])
def proxy(url):
    """Fetches the specified URL and streams it out to the client.

    If the request was referred by the proxy itself (e.g. this is an image fetch for
    a previously proxied HTML page), then the original Referer is passed."""
    r = get_source_rsp(url)

    LOG.info("Got %s response from %s",r.status_code, url)

    # headers = dict(r.headers)

    resp = make_response(r.text)

    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    resp.headers['Access-Control-Max-Age'] = '1000'

    return resp


def get_source_rsp(url):
    url = 'http://127.0.0.1:4242/%s' % url
    LOG.info("Fetching %s", url)
    # Pass original Referer for subsequent resource requests
    proxy_ref = proxy_ref_info(request)
    headers = { "Referer" : "http://%s/%s" % (proxy_ref[0], proxy_ref[1])} if proxy_ref else {}
    # Fetch the URL, and stream it back
    verb = getattr(requests, request.method.lower())
    LOG.info("%s with headers: %s, %s", request.method, url, headers)
    return verb(url, stream=False , params=request.args, headers=headers, data=request.data)


def split_url(url):
    """Splits the given URL into a tuple of (protocol, host, uri)"""
    proto, rest = url.split(':', 1)
    rest = rest[2:].split('/', 1)
    host, uri = (rest[0], rest[1]) if len(rest) == 2 else (rest[0], "")
    return (proto, host, uri)


def proxy_ref_info(request):
    """Parses out Referer info indicating the request is from a previously proxied page.

    For example, if:
        Referer: http://localhost:8080/p/google.com/search?q=foo
    then the result is:
        ("google.com", "search?q=foo")
    """
    ref = request.headers.get('referer')
    if ref:
        _, _, uri = split_url(ref)
        if uri.find("/") < 0:
            return None
        first, rest = uri.split("/", 1)
        if first in "pd":
            parts = rest.split("/", 1)
            r = (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")
            LOG.info("Referred by proxy host, uri: %s, %s", r[0], r[1])
            return r
    return None
