"""Vibe AI initializer."""
import flask
# app is a single object used by all the code modules in this package
vibe = flask.Flask(__name__)  # pylint: disable=invalid-name

# Read settings from config module (insta485/config.py)
vibe.config.from_object('app.config')

import routes