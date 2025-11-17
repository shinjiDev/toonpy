from __future__ import annotations

from hypothesis import given, settings, strategies as st

from toontools import from_toon, to_toon


json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10_000, max_value=10_000),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=40),
)

json_values = st.recursive(
    json_scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=4),
    ),
    max_leaves=20,
)


@settings(max_examples=100)
@given(json_values)
def test_round_trip_property(value):
    toon = to_toon(value)
    parsed = from_toon(toon)
    assert parsed == value

