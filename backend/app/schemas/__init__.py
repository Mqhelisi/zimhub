"""Validation for Stage 1 is kept inline in the route layer with small helper
functions. We don't pull in a separate schema framework — the surface is small
enough that a few field checks are clearer than a full marshmallow setup.

If later stages want a more rigorous schema layer, add it here.
"""
