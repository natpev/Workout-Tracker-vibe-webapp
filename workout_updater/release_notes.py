# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Validate plain release bullets fetched from an already pinned approved commit.

No Markdown/HTML is executed. The host persists this text before installation,
so notes remain available when application containers are stopped.
"""
import json
import re


def read_notes(version, content):
    """Return bounded, version-matched display text; reject missing modern notes."""
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version):
        raise ValueError('Invalid release version.')
    if content is None:
        if tuple(map(int,version.split('.'))) >= (0,12,0):
            raise ValueError('This release is missing its required user-facing notes.')
        return 'Release notes are not available for this older release.'
    if len(content.encode('utf-8'))>32768:
        raise ValueError('Release notes are too large.')
    def unique(pairs):
        """Reject duplicate JSON keys so the version cannot be ambiguous."""
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate release-note field.')
            result[key]=value
        return result
    data=json.loads(content,object_pairs_hook=unique)
    if not isinstance(data,dict) or set(data)!={'version','notes'} or data['version']!=version:
        raise ValueError('Release notes do not match the approved application version.')
    notes=data['notes']
    if not isinstance(notes,list) or not 1<=len(notes)<=20:
        raise ValueError('Provide 1–20 concise release-note bullets.')
    for note in notes:
        if not isinstance(note,str) or not note.strip() or len(note)>500 or len(note.splitlines())!=1 or any(ord(c)<32 or ord(c)==127 for c in note):
            raise ValueError('Each release-note bullet must be one short plain-text line.')
    return '\n'.join('• '+note.strip() for note in notes)
