from flask import Flask, render_template, session
from config import config
from utils.db import check_db_connection
import os


def create_app(config_name=None):
    """Application factory pattern for Flask app initialization."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config["default"]))
    if config_name == "production" and not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set in the environment for production.")

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.trainer_routes import trainer_bp
    from routes.member_routes import member_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(trainer_bp)
    app.register_blueprint(member_bp)

    # Context processor to inject common variables into all templates
    @app.context_processor
    def inject_globals():
        return {
            "current_user_name": session.get("user_name"),
            "current_user_role": session.get("role"),
            "current_user_status": session.get("status"),
            "is_logged_in": "user_id" in session,
        }

    # Public landing page
    @app.route("/")
    def home():
        return render_template("index.html")

    # Diagnostic / Health check endpoint
    @app.route("/health")
    def health_check():
        db_ok, db_msg = check_db_connection()
        return {
            "status": "online",
            "framework": "Flask 3.1",
            "python_version": "3.14.3",
            "database_connected": db_ok,
            "database_message": db_msg,
        }

    # Custom Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errors/500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
