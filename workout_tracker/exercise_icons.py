# SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
"""Strict passive SVG allowlist, SQLite artwork storage and safe inline rendering.

Uploads never become filesystem paths or raw HTML. Canonical shapes are stored
by exercise ID/position; inline rendering inherits the selected person's accent.
"""
from functools import lru_cache
from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET
from markupsafe import Markup
from .catalog import ValidationError

# Bound both uploaded bytes and canonical output; each slot has its own limit.
MAX_BYTES = 300 * 1024
MAX_ELEMENTS=1024
SVG_NS='http://www.w3.org/2000/svg'
ET.register_namespace('',SVG_NS)
TAGS={'svg','g','path','rect','circle','ellipse','line','polyline','polygon','title','desc'}
PAINT={'none','currentColor','black','white','gray','grey','silver','transparent','var(--accent)'}
NUMBER=r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
NUMERIC={'x','y','x1','y1','x2','y2','cx','cy','r','rx','ry','width','height','stroke-width','stroke-miterlimit','opacity','fill-opacity','stroke-opacity'}
COMMON={'fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','fill-rule','clip-rule','opacity','fill-opacity','stroke-opacity','transform'}
ATTRIBUTES={
 'svg':COMMON|{'viewBox','width','height','preserveAspectRatio'}, 'g':COMMON,
 'path':COMMON|{'d'}, 'rect':COMMON|{'x','y','width','height','rx','ry'},
 'circle':COMMON|{'cx','cy','r'},'ellipse':COMMON|{'cx','cy','rx','ry'},
 'line':COMMON|{'x1','y1','x2','y2'},'polyline':COMMON|{'points'},
 'polygon':COMMON|{'points'},'title':set(),'desc':set(),
}


def numbers(value):
    """Parse bounded finite numeric lists without interpreting CSS or URLs."""
    if len(value)>32768 or re.sub(NUMBER,'',value).strip(' ,\t\r\n'):
        raise ValidationError('SVG contains an unsupported numeric value.')
    result=[float(match) for match in re.findall(NUMBER,value)]
    if not result or any(not math.isfinite(number) or abs(number)>1000000 for number in result):
        raise ValidationError('SVG coordinates exceed the supported bounds.')
    return result


def sanitize(source):
    """Reject active/unsupported XML, returning canonical passive SVG only.

    No styles, IDs, links, references, images, HTML, animation, filters or external
    resources are accepted. Comments are discarded; DTDs/entities are refused.
    Only an exact var(--accent) paint token may reference the application palette.
    """
    if isinstance(source,bytes):
        if len(source)>MAX_BYTES:raise ValidationError('SVG must be at most 300 KiB per image.')
        try:source=source.decode('utf-8-sig')
        except UnicodeDecodeError as error:raise ValidationError('SVG must use UTF-8 text.') from error
    if not isinstance(source,str) or len(source.encode('utf-8'))>MAX_BYTES:
        raise ValidationError('SVG must be at most 300 KiB per image.')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)',source,re.I):
        raise ValidationError('SVG document types and entities are not allowed.')
    if '<?' in re.sub(r'^\s*<\?xml\s[^?]*\?>','',source,count=1):
        raise ValidationError('SVG processing instructions are not allowed.')
    try:root=ET.fromstring(source)
    except (ET.ParseError,ValueError) as error:raise ValidationError('Upload a valid SVG document.') from error
    elements=list(root.iter())
    if len(elements)>MAX_ELEMENTS:raise ValidationError('SVG has too many elements (maximum 1024).')
    for index,element in enumerate(elements):
        tag=element.tag
        if tag.startswith('{'):
            namespace,tag=tag[1:].split('}',1)
            if namespace!=SVG_NS:raise ValidationError('Only the SVG namespace is supported.')
        if tag not in TAGS or (tag=='svg' and index!=0) or (index==0 and tag!='svg'):
            raise ValidationError('SVG contains an unsupported element.')
        if tag in ('title','desc'):
            if len(element) or len(element.text or '')>500:raise ValidationError('SVG descriptions must be short plain text.')
        elif (element.text or '').strip():raise ValidationError('Use vector shapes rather than embedded text.')
        if (element.tail or '').strip():raise ValidationError('SVG contains unsupported text.')
        for key,value in list(element.attrib.items()):
            if key not in ATTRIBUTES[tag]:
                raise ValidationError('SVG contains an unsupported attribute.')
            if len(value)>32768:
                raise ValidationError('SVG attribute exceeds the complexity limit (maximum 32768 characters).')
            if key in ('fill','stroke'):
                if value not in PAINT and not re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})',value):
                    raise ValidationError('Use a plain color, currentColor, none, or var(--accent).')
            elif key in NUMERIC:
                parsed=numbers(value)
                if len(parsed)!=1 or (key in ('width','height','r','rx','ry','stroke-width') and parsed[0]<0):
                    raise ValidationError('SVG dimensions must be valid nonnegative numbers.')
                if key in ('opacity','fill-opacity','stroke-opacity') and not 0<=parsed[0]<=1:
                    raise ValidationError('SVG opacity must be between zero and one.')
            elif key=='viewBox':
                box=numbers(value)
                if len(box)!=4 or box[2]<=0 or box[3]<=0:raise ValidationError('SVG needs a valid viewBox.')
            elif key=='d':
                if not re.fullmatch(r'[MmLlHhVvCcSsQqTtAaZz0-9eE+.,\s-]+',value):raise ValidationError('SVG path data is unsupported.')
                numbers(re.sub(r'[MmLlHhVvCcSsQqTtAaZz]',' ',value))
            elif key=='points':
                if len(numbers(value))%2:raise ValidationError('SVG points must be coordinate pairs.')
            elif key=='transform':
                remaining=value
                pattern=r'(?:matrix|translate|scale|rotate|skewX|skewY)\s*\(([^()]*)\)'
                matches=list(re.finditer(pattern,value))
                for match in matches:numbers(match.group(1))
                if not matches or re.sub(pattern,'',remaining).strip(' ,\t\r\n'):raise ValidationError('SVG transform is unsupported.')
            elif key in ('stroke-linecap','stroke-linejoin'):
                if value not in ('butt','round','square','miter','bevel'):raise ValidationError('Unsupported SVG outline.')
            elif key in ('fill-rule','clip-rule'):
                if value not in ('evenodd','nonzero'):raise ValidationError('Unsupported SVG fill rule.')
            elif key=='preserveAspectRatio' and value!='xMidYMid meet':raise ValidationError('SVG must preserve its aspect ratio.')
        element.tag='{'+SVG_NS+'}'+tag
    root.set('viewBox',root.get('viewBox','0 0 256 256'))
    root.set('width','256');root.set('height','256');root.set('preserveAspectRatio','xMidYMid meet')
    result=ET.tostring(root,encoding='unicode')
    if len(result.encode('utf-8'))>MAX_BYTES:raise ValidationError('Canonical SVG exceeds 300 KiB per image.')
    return result


@lru_cache(maxsize=2)
def default(position):
    """Load exactly the two packaged equipment illustrations; no name matching."""
    if position not in ('start','end'):raise ValidationError('Choose Start or End.')
    return sanitize((Path(__file__).parent/'static/exercise-icons'/f'{position}.svg').read_bytes())


def artwork(svg,custom=False):
    """Only validated canonical SVG is marked safe for inline template rendering."""
    safe=sanitize(svg)
    root=ET.fromstring(safe);root.set('aria-hidden','true');root.set('focusable','false')
    return dict(svg=Markup(ET.tostring(root,encoding='unicode')),custom=custom)


def pairs(db,identities):
    """Bulk-read shared artwork once for a page; color remains a CSS variable."""
    result={identity:{position:artwork(default(position)) for position in ('start','end')} for identity in identities}
    if db.execute('PRAGMA user_version').fetchone()[0]>=11:
        for row in db.execute('SELECT * FROM exercise_icons'):
            if row['exercise_id'] in result:result[row['exercise_id']][row['position']]=artwork(row['svg'],True)
    return result


def update(db,exercise,position,source=None):
    """Atomically replace one slot or remove it, leaving the other slot untouched."""
    if position not in ('start','end'):raise ValidationError('Choose Start or End.')
    if db.execute('PRAGMA user_version').fetchone()[0]<11:raise ValidationError('Custom icons require explicit schema-11 migration.')
    if source is None:db.execute('DELETE FROM exercise_icons WHERE exercise_id=? AND position=?',(exercise,position))
    else:
        svg=sanitize(source)
        if db.execute('PRAGMA user_version').fetchone()[0] == 11 and len(svg.encode('utf-8')) > 65536:
            raise ValidationError('Larger icons require an explicit upgrade to database schema 12; the previous icon is unchanged.')
        db.execute('INSERT INTO exercise_icons VALUES (?,?,?) ON CONFLICT(exercise_id,position) DO UPDATE SET svg=excluded.svg',(exercise,position,svg))
