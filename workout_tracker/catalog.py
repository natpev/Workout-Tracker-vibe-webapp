# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""People/exercise/routine rules called by web routes with a locked transaction.

Browser forms -> routes -> these functions -> parameterized SQLite reads/writes.
No function opens a database, commits independently, or handles workout results.
Permanent IDs use UUIDs; archives preserve identity for future snapshot history.
"""

import re
from uuid import uuid4


class ValidationError(ValueError):
    """A user-correctable form error; transactions are rolled back by the caller."""


class MissingRecord(LookupError):
    """The record is missing, archived or does not belong to the selected person."""


def text(value, label, maximum=100):
    """Validate required trimmed text without interpreting markup or SQL."""
    result = str(value or "").strip()
    if not 1 <= len(result) <= maximum:
        raise ValidationError(f"{label} must contain 1–{maximum} characters.")
    return result


def integer(value, label, minimum, maximum):
    """Accept only base-10 whole numbers within documented form limits."""
    value = str(value)
    if not re.fullmatch(r"[0-9]+", value) or len(value) > 9:
        raise ValidationError(f"{label} must be a whole number.")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValidationError(f"{label} must be between {minimum} and {maximum}.")
    return number


def person(connection, person_id, *, archived=False):
    """Read the chosen household person; selection is not authentication."""
    row = connection.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
    if row is None or (row["archived"] and not archived):
        raise MissingRecord("Person not found or archived.")
    return row


def routine(connection, person_id, routine_id):
    """Ownership is checked on every routine operation, not just in the UI."""
    person(connection, person_id)
    row = connection.execute(
        "SELECT * FROM routines WHERE id=? AND person_id=? AND archived=0", (routine_id, person_id)
    ).fetchone()
    if row is None:
        raise MissingRecord("Routine not found for this person.")
    return row


def shared_library(connection):
    """Read the actual schema; legacy schemas retain their original ownership rules."""
    return connection.execute("PRAGMA user_version").fetchone()[0] >= 5


def definitions(connection, person_id):
    """List selectable IDs globally on schema 5, or locally on retained old schemas."""
    person(connection, person_id)
    clause, args = ("", ()) if shared_library(connection) else (" AND person_id=?", (person_id,))
    return connection.execute("SELECT * FROM exercises WHERE archived=0" + clause + " ORDER BY name COLLATE NOCASE,id", args).fetchall()


def unique_name(connection, person_id, name, excluding=None):
    """Prevent new case-insensitive duplicates, without merging old identities.

    Python casefold handles Unicode names; archived definitions also reserve a
    name. Existing migrated duplicates stay separately selectable by permanent ID.
    """
    name = text(name, "Exercise name")
    if shared_library(connection):
        for row in connection.execute("SELECT id,name FROM exercises"):
            if row['id'] != excluding and row['name'].casefold() == name.casefold():
                raise ValidationError("This exercise name is already registered. Select its existing library entry or choose a distinct name.")
    return name


def definition(connection, person_id, exercise_id):
    """Read a shared active identity; old schemas still enforce local ownership."""
    person(connection, person_id)
    clause, args = ("", (exercise_id,)) if shared_library(connection) else (" AND person_id=?", (exercise_id, person_id))
    row = connection.execute("SELECT * FROM exercises WHERE id=? AND archived=0" + clause, args).fetchone()
    if row is None:
        raise MissingRecord("Exercise not found for this person.")
    return row


def create_person(connection, name):
    """Insert a new person with a permanent ID; return it for navigation."""
    identity = uuid4().hex
    connection.execute("INSERT INTO people(id,name) VALUES (?,?)", (identity, text(name, "Name")))
    return identity


def update_person(connection, identity, name, action):
    """Rename/archive/reactivate without deleting any person's records."""
    person(connection, identity, archived=True)
    if action == "rename":
        connection.execute("UPDATE people SET name=? WHERE id=?", (text(name, "Name"), identity))
    elif action in ("archive", "reactivate"):
        connection.execute("UPDATE people SET archived=? WHERE id=?", (int(action == "archive"), identity))
    else:
        raise ValidationError("Unknown person action.")


def create_definition(connection, person_id, name):
    """Create a permanent library ID; person_id records registration provenance."""
    person(connection, person_id)
    identity = uuid4().hex
    connection.execute("INSERT INTO exercises(id,person_id,name) VALUES (?,?,?)",
                       (identity, person_id, unique_name(connection, person_id, name)))
    return identity


def update_definition(connection, person_id, identity, name, action):
    """Rename everywhere this identity is reused; archive without cascading deletes."""
    definition(connection, person_id, identity)
    if action == "rename":
        connection.execute("UPDATE exercises SET name=? WHERE id=?",
                           (unique_name(connection, person_id, name, identity), identity))
    elif action == "archive":
        used = connection.execute(
            "SELECT 1 FROM routine_exercises re JOIN routines r ON r.id=re.routine_id "
            "WHERE re.exercise_id=? AND r.archived=0 LIMIT 1", (identity,)).fetchone()
        if used:
            raise ValidationError("Remove this exercise from active routines before archiving it.")
        connection.execute("UPDATE exercises SET archived=1 WHERE id=?", (identity,))
    else:
        raise ValidationError("Unknown exercise action.")


def create_routine(connection, person_id, name):
    """Insert an empty routine at the end, preserving all existing routine IDs."""
    person(connection, person_id)
    identity = uuid4().hex
    position = connection.execute("SELECT coalesce(max(position),-1)+1 FROM routines WHERE person_id=?",
                                  (person_id,)).fetchone()[0]
    connection.execute("INSERT INTO routines(id,person_id,name,position) VALUES (?,?,?,?)",
                       (identity, person_id, text(name, "Routine name"), position))
    return identity


def configure(values):
    """Convert browser targets to one valid typed configuration, never measurements.

    Only fields for the selected mode are retained. Minute/second inputs become
    a single integer second target, never multiplied by sets. A target must be
    positive; limits bound mistakes without choosing future actual-result rules.
    """
    kind = values.get("measurement_type", "")
    sets = integer(values.get("target_sets", ""), "Sets", 1, 1000)
    notes = str(values.get("notes", "")).strip()
    if len(notes) > 2000:
        raise ValidationError("Notes must contain at most 2000 characters.")
    if kind == "weight":
        reps = integer(values.get("target_reps", ""), "Target reps", 1, 10000)
        meaning = str(values.get("weight_meaning", "")).strip()
        if len(meaning) > 200:
            raise ValidationError("Weight meaning must contain at most 200 characters.")
        return kind, sets, reps, None, "lb", meaning, notes
    if kind == "time":
        minutes = integer(values.get("minutes", ""), "Minutes", 0, 5999)
        seconds = integer(values.get("seconds", ""), "Seconds", 0, 59)
        duration = minutes * 60 + seconds
        if duration == 0:
            raise ValidationError("Target duration must be greater than zero.")
        return kind, sets, None, duration, None, "", notes
    raise ValidationError("Choose Weight or Time.")


def add_entry(connection, person_id, routine_id, values):
    """Add a configuration linked to an existing or newly created permanent exercise."""
    routine(connection, person_id, routine_id)
    configuration = configure(values)
    exercise_id = values.get("exercise_id")
    if exercise_id:
        definition(connection, person_id, exercise_id)
    else:
        exercise_id = create_definition(connection, person_id, values.get("name"))
    identity = uuid4().hex
    position = connection.execute(
        "SELECT coalesce(max(position),-1)+1 FROM routine_exercises WHERE routine_id=?", (routine_id,)
    ).fetchone()[0]
    connection.execute(
        "INSERT INTO routine_exercises(id,person_id,routine_id,exercise_id,position,measurement_type,"
        "target_sets,target_reps,target_duration_seconds,unit,weight_meaning,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (identity, person_id, routine_id, exercise_id, position, *configuration),
    )
    return identity


def entry(connection, person_id, routine_id, entry_id):
    """Load a routine item through both person/routine ownership constraints."""
    routine(connection, person_id, routine_id)
    row = connection.execute(
        "SELECT re.*, e.name FROM routine_exercises re JOIN exercises e ON e.id=re.exercise_id "
        "WHERE re.id=? AND re.routine_id=? AND re.person_id=?", (entry_id, routine_id, person_id)
    ).fetchone()
    if row is None:
        raise MissingRecord("Routine exercise not found for this person.")
    return row


def update_entry(connection, person_id, routine_id, entry_id, values):
    """Edit only routine configuration; permanent exercise identity stays unchanged."""
    entry(connection, person_id, routine_id, entry_id)
    configuration = configure(values)
    connection.execute(
        "UPDATE routine_exercises SET measurement_type=?,target_sets=?,target_reps=?,"
        "target_duration_seconds=?,unit=?,weight_meaning=?,notes=? WHERE id=? AND person_id=? AND routine_id=?",
        (*configuration, entry_id, person_id, routine_id),
    )


def move(connection, table, owner_column, owner_id, identity, direction):
    """Move one routine/item with two-pass positions to respect UNIQUE constraints.

    SQL identifiers are chosen only by our caller, never browser input. Archived
    routines are left in the sequence but are not candidates for UI movement.
    """
    if (table, owner_column) not in (("routines", "person_id"), ("routine_exercises", "routine_id")):
        raise ValueError("Unsupported ordering table")
    if direction not in ("up", "down"):
        raise ValidationError("Choose up or down.")
    active_filter = " AND archived=0" if table == "routines" else ""
    rows = connection.execute(f"SELECT id,position FROM {table} WHERE {owner_column}=?{active_filter} ORDER BY position",
                              (owner_id,)).fetchall()
    identities = [row["id"] for row in rows]
    if identity not in identities:
        raise MissingRecord("Ordered item not found.")
    index = identities.index(identity)
    destination = index + (-1 if direction == "up" else 1)
    if not 0 <= destination < len(identities):
        return
    identities[index], identities[destination] = identities[destination], identities[index]
    positions = [row["position"] for row in rows]
    maximum = connection.execute(f"SELECT coalesce(max(position),0) FROM {table} WHERE {owner_column}=?",
                                 (owner_id,)).fetchone()[0]
    offset = maximum + len(rows) + 1
    for index, current in enumerate(identities):
        connection.execute(f"UPDATE {table} SET position=? WHERE id=?", (offset + index, current))
    for index, current in enumerate(identities):
        connection.execute(f"UPDATE {table} SET position=? WHERE id=?", (positions[index], current))


def copy_routine(connection, source_person, source_id, destination_person, name):
    """Copy settings into fresh routine/items; schema 5 reuses global exercise IDs.

    No results, drafts or recommendations are copied. Older schemas retain their
    local definition copy behavior. Caller commits or rolls back the whole copy.
    """
    routine(connection, source_person, source_id)
    person(connection, destination_person)
    new_routine = create_routine(connection, destination_person, name)
    definitions = {}
    rows = connection.execute(
        "SELECT re.*, e.name FROM routine_exercises re JOIN exercises e ON re.exercise_id=e.id "
        "WHERE re.routine_id=? ORDER BY re.position", (source_id,)).fetchall()
    for row in rows:
        if row["exercise_id"] not in definitions:
            definitions[row["exercise_id"]] = (row["exercise_id"] if shared_library(connection)
                else create_definition(connection, destination_person, row["name"]))
        duration = row["target_duration_seconds"] or 0
        add_entry(connection, destination_person, new_routine, {
            "exercise_id": definitions[row["exercise_id"]], "measurement_type": row["measurement_type"],
            "target_sets": row["target_sets"], "target_reps": row["target_reps"],
            "minutes": duration // 60, "seconds": duration % 60,
            "weight_meaning": row["weight_meaning"], "notes": row["notes"],
        })
    return new_routine
