# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Schema 12 enlarges only the icon constraint on an explicit migration candidate.

The migrator copies the database first. This module never opens the original;
all existing icon text and IDs are copied exactly, with the same foreign keys.
"""
from .interface_schema import INTERFACE_OBJECTS

ICON_SIZE_OBJECTS = dict(INTERFACE_OBJECTS)
ICON_SIZE_OBJECTS['exercise_icons'] = INTERFACE_OBJECTS['exercise_icons'].replace(
    'length(svg) BETWEEN 1 AND 65536',
    'length(CAST(svg AS BLOB)) BETWEEN 1 AND 307200',
)


def upgrade_icon_size(db):
    """Rebuild just the candidate's icon table; retain every original SVG byte."""
    db.execute('CREATE TEMP TABLE preserved_icons AS SELECT * FROM exercise_icons')
    db.execute('DROP TABLE exercise_icons')
    db.execute(ICON_SIZE_OBJECTS['exercise_icons'])
    db.execute('INSERT INTO exercise_icons SELECT * FROM preserved_icons')
    db.execute('DROP TABLE preserved_icons')
