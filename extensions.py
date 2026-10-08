from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Global extensions (used by blueprints)
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Where users get redirected when not logged in
login_manager.login_view = "auth.login"
login_manager.login_message = "Inicie sesión para acceder a esta página."
login_manager.login_message_category = "warning"
