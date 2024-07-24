from flask import Flask

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.secret_key = 'random string'

    from . import openapi
    app.register_blueprint(openapi.bp)
    return app
