# Winslow Product Scraper

Production-grade fashion product scraper for [Winslow](https://winslowla.com/).

## Features

- Scrapes all leaf category collections (Hoodies, Tees, Sweaters, Outerwear, Sweatpants, Hats)
- Uses Shopify `products.json` endpoints (reliable, no JS required for catalog)
- Generates 768-d SigLIP embeddings locally (`google/siglip-base-patch16-384`) — **no HuggingFace API token, no Gemini**
- Optional back-view embeddings when gallery/alt/URL signals a back shot
- Smart diffing: skip unchanged products; only re-embed when image/text fields change
- Batch upserts to Supabase (50/request) with retries
- Stale cleanup after 2 consecutive misses (local tracker)
- GitHub Actions: **Wednesdays 14:17 UTC** + `workflow_dispatch`

## Architecture

```
main.py              # Orchestrates scrape → embed → upsert
config.py            # Brand + env configuration
parser.py            # Shopify products.json extraction
embeddings.py        # Local SigLIP image + text embeddings (from aboutyou pattern)
supabase_client.py   # Batch upsert + stale cleanup
.github/workflows/
  scrape.yml         # Weekly schedule
```

## Setup

### Local

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill SUPABASE_URL and SUPABASE_KEY
python main.py
```

### GitHub Actions

Repository secrets (only):
- `SUPABASE_URL`
- `SUPABASE_KEY`

No HuggingFace token needed — the model runs locally and is cached under `~/.cache/huggingface`.

## Back-view detection

Back shots are detected from image URL/alt keywords (`back`, `rear`, `_b.`, `_back`, etc.). When found:
- `back_image_url` + `back_image_embedding` are set
- URL is also listed in `additional_images`
- `image_url` always stays the front packshot (what the iOS app displays)

## Source fields

- `source`: `scraper-winslow`
- `brand`: `Winslow`
- `second_hand`: `false`
- `embedding_version`: `2` when front embedding is written
