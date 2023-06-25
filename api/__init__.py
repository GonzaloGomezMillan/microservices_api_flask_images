from flask import Flask

def create_app():
    app = Flask(__name__)

    from ..old import views
    app.register_blueprint(views.bp)

    return app