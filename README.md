# The Fall of Thai Governments

A bilingual (English/Thai) data story about Thai politics from 2014 to today.

## Build

```
python3 build_data.py        # writes dist/index.html
SITE_URL=https://<name>.pages.dev python3 build_data.py   # absolute share-image links
```

To refresh the data first: `python3 fetch_bills_votes.py && python3 fetch_votes.py`.

## Data and license

Parliamentary data from [Politigraph](https://politigraph.wevis.info) by [WeVis](https://wevis.info), licensed CC BY-NC 4.0. Not for commercial use. Party logos come from Politigraph and are used only to identify parties.
