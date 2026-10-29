"""Exact allowances for additive Review declarations; frozen science stays strict.

These transformations are used only by source-regression tests. Acquisition and
provenance always retain the complete real source bytes, including these additions.
"""
import hashlib
import re


ADDITIONS = {
    "contrast_sensitivity": ("3228f85a0e29d9848d49df9df92f4b1788004fd0b1d37b7a4153fe866b95ef73", None, "fixed_contrast_method"),
    "ellipse_centre": ("16eaa8012d96c137c2885da4af97e6012cb2fbf8f888793e9e6618bfd6aa4009", "ef06b024fcac27a2c986a8c6066d67a29ba923bc48fa53402c587001b9756024", "constant_contrast_method"),
    "ellipse_major_axis": ("16eaa8012d96c137c2885da4af97e6012cb2fbf8f888793e9e6618bfd6aa4009", "4cf2df0b7cb70f38349c9905ba45564a3dbe06ba9670897ab4a4d95b818edf7e", "constant_contrast_method"),
}


def without_review_additions(source, identity):
    declarations, controls, factory = ADDITIONS[identity]
    patterns = [(r"# Review-only declarations; the actual record functions remain authoritative\.\n.*?# End Review-only declarations\.\n\n\n", declarations)]
    if controls:
        patterns.append((r"        # Review-only control links; acquisition bindings remain unchanged\.\n.*?        # End Review-only control links\.\n", controls))
    for pattern, expected in patterns:
        matches = list(re.finditer(pattern, source, re.S))
        assert len(matches) == 1, "Expected exactly the reviewed additive metadata block"
        block = matches[0].group()
        assert hashlib.sha256(block.encode()).hexdigest() == expected, "Review declaration changed"
        source = source.replace(block, "", 1)
    line = f'        method_reviewer={{"constant_stimuli": {factory}}},\n'
    assert source.count(line) == 1, "The exact reviewed fixed factory must remain declared"
    return source.replace(line, "", 1)
