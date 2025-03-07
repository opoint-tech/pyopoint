"""Check that basic features work.

Catch cases where e.g. files are missing so the import doesn't work."""

from opoint.safefeed.sync import SafefeedClient

client = SafefeedClient("example_key")

# TODO: Make actual test requests.

if client:
    print("Smoke test succeeded")
else:
    raise RuntimeError()
