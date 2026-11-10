# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Structured historical-form validation, separate from atomic storage services.

Routes collect safe field messages before calling existing completion/correction
transactions. Raw submitted strings are kept for rendering; normalized time is
used only for validation/storage. This module never writes SQLite records.
"""
import re
from . import history as h,workouts as w,catalog as c


class FormErrors(c.ValidationError):
    """Carry field messages through a transaction rollback back to the same form."""
    def __init__(self,errors):
        """Retain field-to-message mapping without accepting HTML or technical traces."""
        self.errors=errors
        super().__init__('Please correct the indicated fields before saving.')


def normalized(values):
    """Accept phone-friendly 0930 as 09:30, leaving malformed input intact."""
    result=dict(values);clock=str(result.get('workout_time','')).strip()
    result['workout_time']=clock[:2]+':'+clock[2:] if re.fullmatch(r'[0-9]{4}',clock) else clock
    return result


def occurrence_errors(values,zone):
    """Associate invalid dates, clocks, future occurrence and DST choices with fields."""
    errors={}
    try:h.parse_date(w.field(values,'workout_date'))
    except c.ValidationError as error:errors['workout_date']=str(error)
    clock=str(values.get('workout_time',''))
    if clock and not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?',clock):
        errors['workout_time']='Choose hour 00–23 and minute 00–59 (for example 09:30).'
    if not errors:
        try:h.occurrence(w.field(values,'workout_date'),w.field(values,'workout_time'),zone,w.field(values,'fold'))
        except c.ValidationError as error:
            field='fold' if 'ambiguous' in str(error).lower() or 'earlier' in str(error).lower() else 'workout_time' if clock else 'workout_date'
            errors[field]=str(error)
    return errors


def measurement_errors(rows,values):
    """Collect all exercise errors, preserving blank/zero and one actual per exercise."""
    errors={};performed=False
    for index,row in enumerate(rows):
        fields={key:values.get(f'{key}_{index}','') for key in ('weight','minutes','seconds','increase')}
        try:
            weight,duration,flag=w.measurement(row,fields)
            performed|=weight is not None or duration is not None
        except c.ValidationError as error:
            if isinstance(error,w.MeasurementError):
                errors.update({f'{key}_{index}':row['name']+': '+message for key,message in error.fields.items()})
                continue
            if row['measurement_type']=='weight':keys=[f'weight_{index}']
            else:keys=[f'minutes_{index}',f'seconds_{index}']
            if fields['increase'] not in ('','0','1'):keys=[f'increase_{index}']
            for key in keys:errors[key]=row['name']+': '+str(error)
    if not errors and not performed and values.get('confirm_all_skipped')!='yes':
        errors['confirm_all_skipped']='Confirm saving an entirely skipped workout.'
    return errors


def values_for_rows(parent,rows,correction,display_clock,fold=''):
    """Build GET-only initial values; POST redisplay always uses its raw dictionary."""
    values=dict(workout_date=parent['workout_date'],workout_time=display_clock(parent.get('workout_time')),fold=fold,
                correction_revision=str(parent.get('correction_revision',0)))
    if correction:
        for index,row in enumerate(rows):
            weight=row['actual_weight_tenths_lb'];duration=row['actual_duration_seconds']
            values.update({f'weight_{index}':'' if weight is None else f'{weight//10}.{weight%10}',
                           f'minutes_{index}':'' if duration is None else str(duration//60),
                           f'seconds_{index}':'' if duration is None else str(duration%60),
                           f'increase_{index}':'1' if row['increase_next_time']==1 else ''})
    return values
