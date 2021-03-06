# (c) 2020 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>

from __future__ import annotations

import os.path
import datetime
import sqlite3
import dataclasses
import pytz

from typing import Tuple, Optional, List, Iterator
from cig.data import Event


def now() -> datetime.datetime:
    return datetime.datetime.now(pytz.timezone("Europe/Berlin"))


class Database:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "database.db"))

        with self.conn, open(os.path.join(os.path.dirname(__file__), "..", "schema.sql")) as schema:
            self.conn.executescript(schema.read())

    def maybe_register(self, *, event: int, name: str, admin: bool = False) -> None:
        with self.conn:
            try:
                self.conn.execute("INSERT INTO registrations (event, name, time, admin, deleted) VALUES (?, ?, ?, ?, FALSE)", (event, name, now().isoformat(sep=" "), admin))
            except sqlite3.IntegrityError:
                pass

    def restore(self, *, event: int, name: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE registrations SET deleted = FALSE WHERE event = ? AND name = ?", (event, name))

    def delete(self, *, event: int, name: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE registrations SET deleted = TRUE WHERE event = ? AND name = ?", (event, name))

    def registrations(self, *, event: Event) -> Registrations:
        with self.conn:
            def make_record(row: Tuple[int, int, str, str, bool, bool]) -> Registration:
                return Registration(row[0], row[1], row[2], datetime.datetime.fromisoformat(row[3]), row[4], row[5])

            return Registrations(event, list(map(make_record, self.conn.execute("SELECT id, event, name, time, admin, deleted FROM registrations WHERE event = ? ORDER BY id ASC", (event.id, )))))


@dataclasses.dataclass
class Registration:
    id: int
    event: int
    name: str
    time: datetime.datetime
    admin: bool
    deleted: bool


@dataclasses.dataclass
class Row:
    n: Optional[int]
    name: str
    time: datetime.datetime
    admin: bool
    deleted: bool


class Registrations:
    def __init__(self, event: Event, registrations: List[Registration]):
        self.event = event
        self.registrations = registrations

    def rows(self) -> Iterator[Row]:
        n = 1
        for registration in self.registrations:
            if registration.deleted:
                yield Row(None, registration.name, registration.time, registration.admin, True)
            else:
                yield Row(n, registration.name, registration.time, registration.admin, False)
                n += 1

    def has(self, email: str) -> bool:
        return any(row.name == email for row in self.rows())
