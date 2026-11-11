# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Separate CSRF-protected icon actions; never submit global/routine setting forms.

The upload stream is bounded, sanitized and atomically stored in SQLite. Filenames
are ignored. Invalid uploads roll back and retain the previous working preview.
"""
from flask import Blueprint,request,redirect,url_for,flash
from . import catalog,exercise_icons
from .views import connection,protect_forms

bp=Blueprint('icons',__name__)
bp.before_request(protect_forms)


@bp.post('/people/<person_id>/exercises/<exercise_id>/icons/<position>')
def update(person_id,exercise_id,position):
    """Replace or remove one global icon independently of measurement settings."""
    try:
        with connection(write=True) as db:
            catalog.definition(db,person_id,exercise_id)
            action=request.form.get('action')
            if action=='remove':source=None
            elif action=='upload':
                upload=request.files.get('svg')
                if upload is None or not upload.filename:raise catalog.ValidationError('Choose an SVG file.')
                source=upload.stream.read(exercise_icons.MAX_BYTES+1)
            else:raise catalog.ValidationError('Choose Upload or Remove custom icon.')
            exercise_icons.update(db,exercise_id,position,source)
        flash('Shared exercise icon updated.','success')
    except catalog.ValidationError as error:
        flash('Icon unchanged: '+str(error),'error')
    return redirect(url_for('manage.edit_defaults',person_id=person_id,exercise_id=exercise_id),code=303)
