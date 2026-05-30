"""SchemePro — Flask CLI entry point

Used by Flask-Migrate to create/manage DB migrations:
  - flask db init
  - flask db migrate
  - flask db upgrade

Run with:
  flask --app manage.py db upgrade
or simply:
  flask db upgrade
if your environment resolves the app automatically.
"""

from app import create_app, db

# Expose the Flask app instance for the Flask CLI
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")

