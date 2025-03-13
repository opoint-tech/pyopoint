# Opoint Python Client

The is a client library for interacting with Opoint products.

Initially supports Safefeed.

## Installation

Choose at least one of the web request backends, asyncio or requests

```
pip install opoint[aio]
# OR
pip install opoint[requests]
# OR
pip install opoint[aio,requests]
```

## Safefeed

The Safefeed client comes in two versions, one using `asyncio` and `aiohttp`, and one using `requests`.

Asyncio example:

```python
from opoint.safefeed.aio import SafefeedClient

# Using as an iterator
async with SafefeedClient("your-token-here") as client:
    async for batch in client:
        my_process_batch(batch)

# "Manual" usage
async with SafefeedClient("your-token-here") as client:
    while True:
        batch = await client.get_articles()
        my_process_batch(batch)

```

Requests example:
```python
from opoint.safefeed.sync import SafefeedClient

client = SafefeedClient("your-token-here")
for batch in client:
    my_process_batch(batch)
```

By default, the safefeed client will attempt to make smart decisions about how often to poll the feed and how many articles to ask for based on observed rate of new articles.

If you have any additional requirements, you can customise the parameters `interval`, `num_art`, and `expected_rate`. Unset parameters are adjusted based on observations and the specified parameters. If you set all three of these, all adaptive behaviour will cease. Don't do this unless you are confident in your parameters.

The interval setting sets the actual interval from the start of one request to the start of the next. The program sleeps the remaining time once the next iteration is called.

It is recommended that the batch processing is short, preferably no more than a few seconds even for a full feed, otherwise the interval might be missed. This means you likely want to simply hand the batch off to a thread, put in in a queue, or otherwise do the actual processing either in a different thread or a different program, such that it does not block the feed. For sparse feeds that are called more rarely and have fewer hits this is not a concern.


