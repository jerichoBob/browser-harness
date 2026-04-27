import base64
import io
import tempfile
from unittest.mock import patch

from PIL import Image

import helpers


def _fake_png(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_max_dim_downsizes_oversized_image():
    fake = lambda method, **kwargs: {"data": _fake_png(4592, 2286)}
    with patch("helpers.cdp", side_effect=fake), tempfile.NamedTemporaryFile(suffix=".png") as f:
        helpers.capture_screenshot(f.name, max_dim=1800)
        w, h = Image.open(f.name).size

    assert max(w, h) == 1800


def test_max_dim_skips_when_image_already_small():
    fake = lambda method, **kwargs: {"data": _fake_png(800, 400)}
    with patch("helpers.cdp", side_effect=fake), tempfile.NamedTemporaryFile(suffix=".png") as f:
        helpers.capture_screenshot(f.name, max_dim=1800)
        w, h = Image.open(f.name).size

    assert (w, h) == (800, 400)


def test_max_dim_default_is_no_resize():
    fake = lambda method, **kwargs: {"data": _fake_png(4592, 2286)}
    with patch("helpers.cdp", side_effect=fake), tempfile.NamedTemporaryFile(suffix=".png") as f:
        helpers.capture_screenshot(f.name)
        w, h = Image.open(f.name).size

    assert (w, h) == (4592, 2286)
