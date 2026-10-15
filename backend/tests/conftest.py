import pytest


class _FakeQuery:
    def __init__(self, table: "_FakeTable"):
        self.table = table
        self.filters = []
        self.action = None
        self.payload = None

    def insert(self, records):
        self.action = "insert"
        self.payload = records if isinstance(records, list) else [records]
        return self

    def select(self, *_args):
        self.action = "select"
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.filters.append((column, set(values)))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self.table.rows
        for column, value in self.filters:
            if isinstance(value, set):
                rows = [r for r in rows if r.get(column) in value]
            else:
                rows = [r for r in rows if r.get(column) == value]

        if self.action == "insert":
            for record in self.payload:
                record.setdefault("id", f"id-{len(self.table.rows) + 1}")
                self.table.rows.append(record)
            return _Result(self.payload)

        if self.action == "update":
            for row in rows:
                row.update(self.payload)
            return _Result(rows)

        return _Result(rows)


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self):
        self.rows: list[dict] = []

    def query(self):
        return _FakeQuery(self)


class FakeSupabase:
    def __init__(self):
        self._tables: dict[str, _FakeTable] = {}

    def table(self, name: str) -> _FakeQuery:
        self._tables.setdefault(name, _FakeTable())
        return self._tables[name].query()


@pytest.fixture
def fake_db():
    return FakeSupabase()
