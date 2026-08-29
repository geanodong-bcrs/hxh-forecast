# Hunter x Hunter — publication forecast

**[View the forecast](https://geanodong-bcrs.github.io/hxh-forecast/)** ·
[How it works](https://geanodong-bcrs.github.io/hxh-forecast/method.html)

A Bayesian forecast of when the next Hunter x Hunter chapters will be published,
built from the historical publication record and from Togashi's own production
posts on X. It updates itself: once a day, and again whenever he posts.

This repository is the published output and the code that produces it. Every
forecast the model has ever made is in `data/forecasts/`, append-only — including
the wrong ones.

## What is here

```
index.html          the forecast page
method.html         how it works, and where it is weakest
scripts/            the whole pipeline: fetch -> build -> forecast -> render
docs/               data dictionary, model, backtest, event taxonomy, automation
data/processed/     chapters, WSJ issue calendar, tweets, production events
data/forecasts/     every forecast snapshot, never overwritten
data/annotations/   image transcriptions and the announcement record
Agents.md           the project specification the whole thing follows
```

## What is deliberately not here

Togashi's manuscript photos. The project downloads them to transcribe production
milestones, which is why `data/raw/` is missing from this repository — archiving
them for research is one thing, republishing several hundred of them is another.
`data/processed/production_events.csv` carries the verbatim Japanese read from
each image, with the tweet ID it came from, so the evidence is auditable without
the images being rehosted.

## Reproducing a forecast

Every snapshot records the sha256 of each input file it was built from, plus the
run that produced it and the evidence timestamp it was allowed to see.

```bash
python3 scripts/run_update.py --no-poll --force
```

## Caveats

The model's headline number rests on very little, and the method page says so
plainly rather than burying it. No calibration figures are published yet, because
scoring honestly requires an announcement record that does not exist yet — see
`docs/model.md` and `docs/backtest.md`.

An independent fan project. Not affiliated with Shueisha or with Togashi.
