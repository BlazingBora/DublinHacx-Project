import re
import uuid

from flask import g, request

# Each browser/app install gets its own private inventory, keyed by a
# random id. Browsers keep it in a long-lived cookie; the mobile app (or
# any API client) can send it explicitly in the X-Device-Id header.
COOKIE_NAME = "xpirescan_device"
HEADER_NAME = "X-Device-Id"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 years

_VALID_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def get_device_id():
    """Returns this request's device id, minting a new one if it has none."""

    if "device_id" in g:
        return g.device_id

    device_id = request.headers.get(HEADER_NAME) or request.cookies.get(COOKIE_NAME)

    if not device_id or not _VALID_ID.match(device_id):
        device_id = uuid.uuid4().hex
        g.new_device_id = True

    g.device_id = device_id
    return device_id


def init_app(app):
    @app.after_request
    def _set_device_cookie(response):
        # Mint the id on every request (not just ones touching the DB) so
        # the cookie exists before the first form submit.
        if request.endpoint != "static":
            get_device_id()

        if g.get("new_device_id"):
            response.set_cookie(
                COOKIE_NAME,
                g.device_id,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
                secure=request.is_secure,
            )

        return response
