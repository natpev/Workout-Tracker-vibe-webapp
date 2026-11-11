# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Permanent basis independent of current mode; called inside catalog transactions.

First explicit assignment writes one immutable shared row. Later type corrections
reuse it, including after duration-only use. No snapshots or history are modified.
"""
from .catalog import ValidationError


def assigned(db,exercise):
    """Read the exercise's lifetime convention, including a dormant assignment."""
    row=db.execute('SELECT basis FROM exercise_weight_basis WHERE exercise_id=?',(exercise,)).fetchone()
    return row[0] if row else None


def configuration(db,exercise,current,values,confirmed=False):
    """Validate type correction consent and reject any assigned-basis workaround."""
    kind=values.get('measurement_type');basis=assigned(db,exercise)
    if kind!=current['measurement_type'] and not confirmed:
        raise ValidationError('Confirm this measurement-type correction before saving.')
    selected=values.get('weight_basis')
    if basis:
        if selected not in (None,'',basis) and not (kind=='time' and selected=='not_configured'):
            raise ValidationError('Weight Basis is permanent, including after a duration-only correction.')
        selected=basis
    elif kind!='time':
        if selected not in ('total','per_side'):
            raise ValidationError('Choose the initial permanent Weight Basis for this weight-based exercise.')
    else:selected='not_configured'
    return dict(values,weight_basis=selected,weight_meaning=current['weight_meaning'])


def ensure(db,exercise,kind,basis):
    """Append first assignment only; callers validate before any configuration write."""
    if kind=='time':return
    previous=assigned(db,exercise)
    if previous and previous!=basis:raise ValidationError('Weight Basis is permanent.')
    if previous is None:
        if basis not in ('total','per_side'):raise ValidationError('Choose a permanent Weight Basis.')
        db.execute('INSERT INTO exercise_weight_basis VALUES (?,?)',(exercise,basis))
        # Existing duration defaults retain their mode and gain dormant metadata.
        db.execute('UPDATE exercise_defaults SET weight_basis=? WHERE exercise_id=?',(basis,exercise))
