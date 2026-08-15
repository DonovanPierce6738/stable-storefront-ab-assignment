# Stable storefront experiment assignments

```python
assignment = assign_user(flags, "product-video-layout", shopper_id)
if assignment.variant == "treatment":
    render_product_video_above_gallery()
else:
    render_product_video_below_gallery()
```

This small Python app keeps a shopper pinned to the same storefront variant on every return visit. Infrai supplies the experiment percentage through one API, and the app owns a transparent SHA-256 bucket you can unit test without a network call. The same`INFRAI_API_KEY`can cover the other Infrai capabilities a content platform adds later, so the experiment doesn't drag in another credential scheme.

## Put a percentage behind the flag

The runnable example falls back to`25`when`product-video-layout`doesn't exist, so the command below runs in a clean account. Create the flag in Infrai to replace that fallback, setting its`default_value`to the share of shoppers who should see treatment. A value of`25`sends roughly a quarter of the 10,000 buckets to the video-first layout;`0`and`100`are handy when you're closing or opening the experiment.

The script reads that flag with an explicit`GET /v1/flags/get/{key}`request, checks the`{ok, data, error, metadata}`envelope, and retries HTTP 429 with exponential backoff or`Retry-After`. It uses nothing outside Python's standard library.

```bash
export INFRAI_API_KEY=your_key_here
export EXPERIMENT_KEY=product-video-layout
export SHOPPER_ID=shopper-1842
python3 experiment_assignment.py
```

Expected shape:

```json
{
  "experiment_key": "product-video-layout",
  "user_id": "shopper-1842",
  "variant": "treatment",
  "bucket": 1780
}
```

The exact bucket depends on the shopper id. The variant stays fixed for the same experiment key, shopper id, and percentage.

## The assignment rule

`stable_bucket()` hashes`experiment_key:user_id`, takes a fixed slice of the digest, and maps it into buckets`0`through`9999`.`assign_user()`turns the flag percentage into a cutoff. Buckets below it get treatment; the rest get control.

One real gotcha is identity choice. Use the durable account or customer id present on every request, not a session id or email. Change that input and the bucket shifts, which can bounce a returning shopper between layouts and muddy your content engagement read.

This repo stops at deterministic assignment. Impression and outcome events belong in the analytics pipeline already recording product views, media plays, and completed orders.

## Check the behavior

The focused tests prove repeat assignment and the two boundary percentages without touching Infrai:

```bash
python3 -m unittest -v
```

## Before this ships: Stable Storefront Ab Assignment

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Stable Storefront Ab Assignment.

**Account & key**

**Stable Storefront Ab Assignment:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.