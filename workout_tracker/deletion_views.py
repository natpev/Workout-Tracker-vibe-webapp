# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Dedicated household impact review and atomic permanent-deletion routes.

No ordinary routine removal is routed here. GET previews exact current impact;
POST checks CSRF, typed phrase and stale-state fingerprint.
"""
from flask import Blueprint, redirect, render_template, request, url_for, abort, flash
from . import deletions
from .views import connection, protect_forms
from .catalog import person

bp=Blueprint('deletion',__name__)
bp.before_request(protect_forms)


@bp.route('/people/<person_id>/permanent-delete/<kind>/<identity>',methods=['GET','POST'])
def review(person_id,kind,identity):
    """Review/confirm household impact; caller transaction rolls every failure back."""
    if kind not in ('exercise','routine'): abort(404)
    with connection(write=request.method=='POST') as db:
        selected=person(db,person_id)
        if request.method=='POST':
            function=deletions.delete_exercise if kind=='exercise' else deletions.delete_routine
            function(db,person_id,identity,request.form)
        else: impact=deletions.impact(db,kind,identity,person_id)
    if request.method=='POST':
        if kind=='exercise':flash('Exercise permanently deleted.','success')
        return redirect(url_for('manage.exercises' if kind=='exercise' else 'manage.dashboard',person_id=person_id),code=303)
    return render_template('delete_review.html',person=selected,kind=kind,identity=identity,impact=impact)
