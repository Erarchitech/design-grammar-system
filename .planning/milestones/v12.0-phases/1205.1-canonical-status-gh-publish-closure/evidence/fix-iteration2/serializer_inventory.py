"""Observe Pydantic Any serialization separately from the closed admission domain."""
from collections import deque, UserDict, namedtuple
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from pydantic import TypeAdapter
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'data-service'))
import evidence_contract as c

@dataclass
class Record:
    x: object

class CustomIterable:
    def __iter__(self):
        yield float('nan')

factories = {'list': lambda n: [n], 'tuple': lambda n: (n,), 'set': lambda n: {n},
 'frozenset': lambda n: frozenset([n]), 'deque': lambda n: deque([n]),
 'generator': lambda n: (v for v in [n]), 'iterator': lambda n: iter([n]),
 'dataclass': lambda n: Record(n), 'namedtuple': lambda n: namedtuple('Point','x')(n),
 'custom_mapping': lambda n: UserDict(x=n), 'custom_iterable': lambda n: CustomIterable()}
rows = []
for name, factory in factories.items():
    for label, number in [('finite', 1.5), ('nan', float('nan'))]:
        row = {'container': name, 'value': label}
        try:
            row['serializer_json'] = TypeAdapter(object).dump_json(factory(number)).decode()
        except Exception as exc:
            row['serializer_error'] = type(exc).__name__
        try:
            c.validate_json_resources({'x': factory(number)})
            row['guard'] = 'admitted'
        except ValueError:
            row['guard'] = 'rejected'
        assert row['guard'] == ('admitted' if name in ('list', 'tuple') and label == 'finite' else 'rejected')
        rows.append(row)
print(json.dumps(rows, indent=2))
