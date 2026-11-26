# Stage 2 user screenshot inputs

For a report date, store original screenshot files under:

`production/input/screenshots/YYYY-MM-DD/`

Store the matching sidecar at:

`production/input/market-screenshot-observations-YYYY-MM-DD.json`

The sidecar must follow `market-screenshot-observations.schema.json`. Each observation identifies one fixture row by group/name and exact Investing.com source URL. Each captured field independently records its visible label, value, original image path, SHA-256 and capture time. The parser recomputes SHA-256 and rejects missing/out-of-repository images, mismatched dates, wrong URLs, unsupported field labels, or duplicate item identities.

Do not commit screenshots without a sidecar. Do not commit a sidecar without its source image. Do not reuse screenshots from a different report/trading date. Screenshot-provided fields take precedence and must not be overwritten by a browser fetch; only missing fields are eligible for Stage 2 page reads.

A ChatGPT conversation attachment is not automatically available to GitHub Actions. To make a screenshot available to the scheduled main runner, the original image and sidecar must be added to this input path on main before the run.
