import os
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from forms import AVATAR_EXTENSIONS, AvatarUploadForm, ChangePasswordForm, EditProfileForm

# ----------------------------------------------------------
# BLUEPRINT (mounted at /profile)
# ----------------------------------------------------------
profile = Blueprint("profile", __name__, template_folder="templates")

INVALID_FORMAT_MESSAGE = "Formato no permitido. Use PNG, JPG, GIF o WEBP."


def _avatar_filename(user_id, extension, folder):
    """Build '<user_id>_<UTC timestamp with microseconds>.<ext>' that does not exist yet."""
    while True:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        filename = f"{user_id}_{timestamp}.{extension}"
        if not os.path.exists(os.path.join(folder, filename)):
            return filename


def _remove_previous_avatar(user_id, previous, folder):
    """Delete the previous avatar only when it was uploaded by this same user."""
    if not previous or os.path.basename(previous) != previous:
        return
    if not previous.startswith(f"{user_id}_"):
        return
    path = os.path.join(folder, previous)
    if os.path.isfile(path):
        os.remove(path)


# ==========================================================
# 1) VIEW PROFILE
# ==========================================================
@profile.route("/")
@login_required
def view_profile():
    return render_template(
        "profile.html", user=current_user, avatar_form=AvatarUploadForm()
    )


# ==========================================================
# 2) UPDATE AVATAR
# ==========================================================
@profile.route("/avatar", methods=["POST"])
@login_required
def update_avatar():
    form = AvatarUploadForm()

    if not form.validate_on_submit():
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
        return redirect(url_for("profile.view_profile"))

    uploaded = form.avatar.data
    safe_name = secure_filename(uploaded.filename or "")
    extension = os.path.splitext(safe_name)[1].lower().lstrip(".")
    if extension not in AVATAR_EXTENSIONS:
        flash(INVALID_FORMAT_MESSAGE, "danger")
        return redirect(url_for("profile.view_profile"))

    folder = current_app.config["AVATAR_UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = _avatar_filename(current_user.id, extension, folder)
    uploaded.save(os.path.join(folder, filename))

    # Persist the new avatar first; the old file is removed only after the commit succeeds.
    previous = current_user.avatar
    current_user.avatar = filename
    db.session.commit()
    _remove_previous_avatar(current_user.id, previous, folder)

    flash("Foto de perfil actualizada correctamente.", "success")
    return redirect(url_for("profile.view_profile"))


# ==========================================================
# 3) EDIT PROFILE INFO
# ==========================================================
@profile.route("/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user, user=current_user)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data or None
        db.session.commit()

        flash("Perfil actualizado correctamente.", "success")
        return redirect(url_for("profile.view_profile"))

    return render_template("profile_edit.html", form=form, user=current_user)


# ==========================================================
# 4) CHANGE PASSWORD
# ==========================================================
@profile.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm(user=current_user)

    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()

        flash("Contraseña actualizada correctamente.", "success")
        return redirect(url_for("profile.view_profile"))

    return render_template("change_password.html", form=form, user=current_user)
