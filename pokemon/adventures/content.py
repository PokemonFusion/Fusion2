"""Plan and install the fixed Adventure Hall, board and private room pool."""

from dataclasses import dataclass
from hashlib import sha256

from django.db import connection, transaction
from django.db.models import F, Q
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from .constants import (
    ADVENTURE_BOARD_ATTR,
    ADVENTURE_CONTENT_ID_ATTR,
    ADVENTURE_HALL_ATTR,
    ADVENTURE_INSTANCE_ATTR,
    ADVENTURE_OFFERS_ATTR,
)
from .templates import get_template_revision, validate_template


VERSION_ATTR = "adventure_content_version"
INSTALL_LOCK = int.from_bytes(sha256(b"fusion2:adventure-hall").digest()[:8], "big", signed=True)
ROOM = "typeclasses.rooms.FusionRoom"
EXIT = "typeclasses.exits.Exit"
BOARD = "typeclasses.objects.Object"


@dataclass(frozen=True)
class AdventureContent:
    """A supported installation release and its posted mission revisions."""

    version: int
    offers: dict[str, int]

    def validate(self):
        """Check published offers before inspecting or writing world objects."""

        if type(self.version) is not int or self.version < 1:
            raise ValueError("Adventure content version must be a positive integer.")
        for key, version in self.offers.items():
            template = get_template_revision(key, version) if type(version) is int else None
            if template is None or template.status != "active":
                raise ValueError(f"Mission {key} v{version} is unavailable.")
            if errors := validate_template(template):
                raise ValueError(f"Mission {key} v{version}: {'; '.join(errors)}")


CURRENT_CONTENT = AdventureContent(1, {"alpha_meadow": 1})


@dataclass(frozen=True)
class WorldObject:
    """Stable managed identity and expected legacy placement."""

    identity: str
    key: str
    typeclass: str
    aliases: tuple[str, ...] = ()
    location: str | None = None
    destination: str | None = None
    marker: str | None = None
    description: str = ""


OBJECTS = (
    WorldObject("hall", "Adventure Hall", ROOM, ("adventures",), marker=ADVENTURE_HALL_ATTR,
                description="A staging room for solo expeditions. An Adventure Mission Board hangs here."),
    WorldObject("instance-1", "Adventure Instance Room #1", ROOM, ("adventure instance 1",),
                marker=ADVENTURE_INSTANCE_ATTR, description="A private Adventure instance."),
    WorldObject("entrance", "adventures", EXIT, ("adventure", "adv"), "host", "hall"),
    WorldObject("return", "back", EXIT, ("out",), "hall", "host"),
    WorldObject("board", "Adventure Mission Board", BOARD, ("mission board",), "hall",
                description="Use +adventure/board to browse missions and +adventure/take <mission> to enter."),
)


class AdventureInstallation:
    """Validate one world layout and transactionally apply its managed fields."""

    def __init__(self, host_id, content=CURRENT_CONTENT):
        self.host_id = host_id
        self.content = content
        self.objects = {}
        self.created = []

    def _find(self, spec, managed):
        """Match an exact identity or an unambiguous legacy object."""

        existing = managed.get(spec.identity)
        names = {spec.key.lower()}
        if spec.identity == "instance-1":
            names.add("adventure instance room 1")
        if spec.location:
            names.update(spec.aliases)
        source = self.objects.get(spec.location)
        manager = ObjectDB.objects
        candidates = manager.none()
        if not spec.location or source is not None:
            query = Q(db_key__iexact=spec.key)
            for name in names:
                query |= Q(db_key__iexact=name)
            if spec.location:
                query |= Q(db_tags__db_tagtype="alias", db_tags__db_key__in=names)
            if spec.marker:
                query |= Q(db_attributes__db_key=spec.marker, db_attributes__db_category__isnull=True)
            candidates = manager.filter(query)
            if source is not None:
                candidates = candidates.filter(db_location=source)
        matches = {obj.pk: obj for obj in candidates.distinct() if (
            not spec.marker or obj.db_key.lower() in names
            or obj.attributes.get(spec.marker)
        )}
        if existing is not None:
            matches[existing.pk] = existing
        if len(matches) > 1:
            ids = ", ".join(f"#{pk}" for pk in sorted(matches))
            raise ValueError(f"{spec.identity} is ambiguous ({ids}). Resolve the conflicting identities.")
        obj = next(iter(matches.values()), None)
        if obj is None:
            return None
        target = self.objects.get(spec.destination)
        if (obj.db_typeclass_path != spec.typeclass
                or obj.db_location_id != getattr(source, "pk", None)
                or obj.db_destination_id != getattr(target, "pk", None)
                or (spec.destination and target is None)
                or (spec.marker and obj.attributes.get(spec.marker) not in (True, "True", "true", 1))
                or (spec.identity == "board" and existing is None)
                or obj.pk == self.host_id):
            raise ValueError(f"{spec.identity} conflicts with #{obj.pk} ({obj.key}). Review its type, marker and path.")
        return obj

    def plan(self):
        """Inspect current identities, paths and version without writing."""

        self.content.validate()
        host = ObjectDB.objects.filter(pk=self.host_id).first()
        if (host is None or host.db_location_id or host.db_destination_id
                or getattr(host, "_content_types", ()) != ("room",)):
            raise ValueError(f"#{self.host_id} must identify the public room linking to Adventure Hall.")
        self.objects = {"host": host}
        managed = {}
        for obj in ObjectDB.objects.get_by_attribute(
            key=ADVENTURE_CONTENT_ID_ATTR, category="adventure_install",
        ).distinct():
            obj.attributes.reset_cache()
            identity = obj.attributes.get(ADVENTURE_CONTENT_ID_ATTR, category="adventure_install")
            if identity not in {spec.identity for spec in OBJECTS}:
                raise ValueError(f"Unknown Adventure content identity {identity!r} on #{obj.pk}.")
            if identity in managed:
                raise ValueError(f"Duplicate Adventure identity {identity} on #{managed[identity].pk} and #{obj.pk}.")
            managed[identity] = obj
        for spec in OBJECTS:
            self.objects[spec.identity] = self._find(spec, managed)

        hall, instance, board = (self.objects[key] for key in ("hall", "instance-1", "board"))
        if hall is not None and instance == hall:
            raise ValueError(f"Room #{hall.pk} matches both the Hall and instance identities.")
        current = hall.attributes.get(VERSION_ATTR, default=0) if hall else 0
        if type(current) is not int or not 0 <= current <= self.content.version:
            raise ValueError(f"Cannot install v{self.content.version} over installed version {current!r}.")
        if hall is not None:
            misplaced_entrance = ObjectDB.objects.filter(
                db_destination=hall, db_key__iexact="adventures",
            ).exclude(db_location=host).first()
            if misplaced_entrance is not None:
                raise ValueError(f"Entrance #{misplaced_entrance.pk} links the Hall from a different public room.")
            configured_pool = hall.attributes.get("adventure_instance_rooms")
            if configured_pool is not None and (
                instance is None or configured_pool not in ([], [instance], [instance.dbref], instance.dbref)
            ):
                raise ValueError(f"Hall #{hall.pk} has a different configured pool. Review room references before adoption.")
            linked_board = hall.attributes.get(ADVENTURE_BOARD_ATTR)
            if linked_board is not None and linked_board != board:
                raise ValueError(f"Hall #{hall.pk} points to a different mission board.")
        if current and any(self.objects[spec.identity] is None for spec in OBJECTS):
            raise ValueError("Managed Adventure content is incomplete. Restore the missing identity before upgrading.")
        if current and any(managed.get(spec.identity) != self.objects[spec.identity] for spec in OBJECTS):
            raise ValueError("Installed Adventure content has unmarked objects. Resolve the missing identity before upgrading.")

        if current == self.content.version:
            self._validate_installed(hall, instance, board)
        actions = []
        for spec in OBJECTS:
            obj = self.objects[spec.identity]
            if obj is None:
                actions.append(f"Create {spec.identity} ({spec.key})")
            else:
                action = "Keep" if current == self.content.version else "Update" if current else "Adopt"
                actions.append(f"{action} {spec.identity} ({obj.dbref})")
        return actions, current

    def _validate_installed(self, hall, instance, board):
        """Fail on drift in fields controlled by the current release."""

        if (list(hall.attributes.get("adventure_instance_rooms") or []) != [instance]
                or hall.attributes.get(ADVENTURE_BOARD_ATTR) != board
                or board.attributes.get(ADVENTURE_OFFERS_ATTR) != self.content.offers):
            raise ValueError("Installed Adventure pool or board differs from this release. Review managed fields.")
        for room in (hall, instance):
            if room.db.allow_hunting is not False or room.db.noitem is not True:
                raise ValueError(f"Room #{room.pk} differs from the installed hunting/item policy.")

    def _apply(self):
        """Create missing objects and assign only installer-managed data."""

        for spec in OBJECTS:
            obj = self.objects[spec.identity]
            if obj is None:
                obj = create_object(
                    spec.typeclass, key=spec.key, nohome=True, aliases=list(spec.aliases),
                    location=self.objects.get(spec.location), destination=self.objects.get(spec.destination),
                    locks="get:false()" if spec.identity == "board" else None,
                )
                self.objects[spec.identity] = obj
                self.created.append(obj)
                if spec.description:
                    obj.db.desc = spec.description
            obj.attributes.add(ADVENTURE_CONTENT_ID_ATTR, spec.identity, category="adventure_install")
            if spec.marker:
                obj.attributes.add(spec.marker, True)
                obj.db.allow_hunting = False
                obj.db.noitem = True
        hall = self.objects["hall"]
        board = self.objects["board"]
        hall.db.adventure_instance_rooms = [self.objects["instance-1"]]
        hall.db.adventure_board = board
        board.attributes.add(ADVENTURE_OFFERS_ATTR, self.content.offers)
        hall.db.adventure_content_version = self.content.version

    def install(self):
        """Replan under a global writer lock and commit the entire release."""

        try:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [INSTALL_LOCK])
                elif connection.vendor == "sqlite":
                    # Acquire SQLite's writer lock before taking the plan snapshot.
                    ObjectDB.objects.filter(pk=self.host_id).update(db_key=F("db_key"))
                else:
                    raise ValueError("Adventure installation supports PostgreSQL and SQLite.")
                actions, current = self.plan()
                if current != self.content.version:
                    for identity in ("instance-1", "hall"):
                        if obj := self.objects[identity]:
                            ObjectDB.objects.select_for_update().get(pk=obj.pk)
                    self._apply()
                return actions
        except Exception:
            for obj in self.objects.values():
                if obj is not None and obj not in self.created:
                    obj.attributes.reset_cache()
                    obj.contents_cache.init()
            for obj in self.created:
                ObjectDB.flush_cached_instance(obj)
            raise
