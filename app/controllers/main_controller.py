"""
CONTROLLER: Main / Page Routes
Serves the landing page, about page, and the SPA shell.
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page — SEO friendly, lists subjects by level."""
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About & FAQ page."""
    return render_template('about.html')


@main_bp.route('/app')
def spa():
    """Single Page Application shell — scheme generator."""
    return render_template('spa.html')


@main_bp.route('/admin-panel')
def admin_redirect():
    """Guard: redirect non-admins away."""
    if not current_user.is_authenticated or not current_user.is_admin():
        return redirect(url_for('main.index'))
    return render_template('admin.html')
