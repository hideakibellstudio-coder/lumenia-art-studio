"""The bridge releases the GIL only where it is safe and worth it (S2.7, ARCcC 15.4).

The interface thread is the only caller of the engine facade, and the GIL is what serializes it with
the background Python threads. Releasing it inside a facade call would let a background thread reach
the same engine at the same time, and the facade is not reentrant. So a release is allowed only where
the work touches objects the call owns (a snapshot, a decoded layer, a preview buffer): the table in
bridge/README.md ("Política do GIL") lists them, and this test counts the releases in the bindings
so that a new one has to be added there on purpose.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDINGS = ROOT / "bridge" / "core" / "bindings"

# file -> number of `py::gil_scoped_release` it may hold (encode_layer has two: the compression and the copy)
DOCUMENTED = {
    "bind_math_brush.cpp": 1,   # render_stroke_preview
    "bind_persistence.cpp": 3,  # LayerSnapshot.encode_layer (2), decode_layer_tiles (1)
}


def _releases() -> dict[str, int]:
    found = {}
    for path in sorted(BINDINGS.glob("*.cpp")):
        count = path.read_text(encoding="utf-8").count("py::gil_scoped_release")
        if count:
            found[path.name] = count
    return found


def test_the_gil_is_released_only_where_the_policy_lists_it():
    assert _releases() == DOCUMENTED, (
        "the bindings release the GIL somewhere the policy does not list (or stopped doing it): "
        "decide whether the work touches only objects the call owns, then update the table in "
        "bridge/README.md ('Política do GIL') and DOCUMENTED here"
    )


def test_the_readme_states_the_policy_and_names_each_released_call():
    readme = (ROOT / "bridge" / "README.md").read_text(encoding="utf-8")
    assert "## Política do GIL" in readme
    for name in ("encode_layer", "decode_layer_tiles", "render_stroke_preview"):
        assert name in readme.split("## Política do GIL", 1)[1].split("\n## ", 1)[0], name
