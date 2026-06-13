"""Creator type registry — CreatorPlatform_Spec.md §5.0.

The host stores a creator's types as an ARRAY(String) on `creator_profiles`
(the Stage 1 shell's representation). The registry of *which* types exist and
*which page modules* each unlocks is small and fixed for V1, so it lives here
in code rather than a join table — adding a type is a one-line edit, satisfying
the spec's "data-driven and extensible, no core-profile schema change" intent.
"""

# key → {label, modules}. `modules` are the page modules a type unlocks.
CREATOR_TYPES = {
    'musician':      {'label': 'Musician',      'modules': ['music']},
    'photographer':  {'label': 'Photographer',  'modules': ['gallery_photo']},
    'visual_artist': {'label': 'Visual Artist', 'modules': ['gallery_art']},
}

# Modules every creator gets regardless of type.
COMMON_MODULES = ['profile', 'events']


def registry_payload():
    """Public list form for GET /api/creators/types."""
    return [
        {'key': k, 'label': v['label'], 'enabled_modules': v['modules']}
        for k, v in CREATOR_TYPES.items()
    ]


def modules_for_types(types):
    """Union of page modules unlocked by a list of type keys (+ common)."""
    mods = list(COMMON_MODULES)
    for t in (types or []):
        for m in CREATOR_TYPES.get(t, {}).get('modules', []):
            if m not in mods:
                mods.append(m)
    return mods


def is_musician(types):
    return 'musician' in (types or [])


def has_gallery(types):
    return bool({'photographer', 'visual_artist'} & set(types or []))
