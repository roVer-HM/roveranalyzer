from typing import Dict

from flask import Flask
from flask_caching import Cache

from roveranalyzer.analysis.common import Simulation
from roveranalyzer.analysis.flaskapp.config import CacheConfig, FlaskConfigDbg

# cache = Cache(config=CacheConfig)


def init_app(simulations: Dict[str, Simulation]):
    app = Flask(__name__, instance_relative_config=False)

    app.config.from_object(FlaskConfigDbg())

    # cache.init_app(app)
    # cache.cache._client.behaviors({"tcp_nodelay": True})

    with app.app_context():
        # core Flask app...
        # dash application
        from . import dcd_dashboard as d, routes

        app = d.create_dashboard(app, simulations)

        return app
