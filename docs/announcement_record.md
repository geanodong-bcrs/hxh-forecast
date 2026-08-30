# The Publisher-Announcement Record (step 6a) — source survey

Phase 1A step 6a is the one deferred piece of the data layer. `Agents.md` §12
says what it must hold; nothing has ever been collected. This is the survey of
what the record needs, which sources can supply it, which cannot, and what the
first eight announcement dates already say about the model.

Gathered 2026-08-29. Nothing here has been written into `data/`.

## What exists today is not an announcement record

`data/annotations/announcements.csv` holds two rows, for ch. 419 and ch. 420.
Both have an **empty `announcement_date`**, both are marked `confidence=high`,
and both name `"WSJ 次号予告 / reviewer report"` as the source. Neither is an
announcement: the 419 note says outright that the date is not established, and
Togashi's 2026-04-08 post 「420話〜の掲載時期はジャンプ編集部の発表をお待ち
ください」 says the timing of 420 onward is still with the editorial department.
Searching for a publisher announcement of either chapter finds none. They are
reviewer inference about a schedule, recorded in the announcement file.

That matters more than it looks, because of how the file is read.
`scripts/build_posterior.py:48` loads it and then:

```python
end_seq = last_obs + len(ann)
floor_seq = end_seq + 1
```

The **row count** sets where batch 49 ends and therefore the earliest issue
batch 50 can start. The `announcement_date` column is never read by anything.
So the live forecast already depends on this file — through its length, via
rows that are not announcements — while the field the record exists for is
inert.

The consequence for step 6a: **historical announcements must not be appended to
this file.** Sixteen historical rows would push `floor_seq` sixteen issues into
the future and silently corrupt the batch-50 forecast. The historical record
wants its own file; this one is a live schedule stub and should be renamed to
say so.

## Two consumers, and only one of them needs history

The record is blocking two different things, and they have different shapes.

**The live record** feeds `Agents.md` §20 — splitting forecasts made before an
announcement from those made after, which is what README limitations 4 and 8
say is blocking every calibration figure on the site. That split applies to
forecasts *this system emitted*, and the oldest snapshot on disk is
2026-08-28. It needs the announcement for 419/420 and a habit of recording each
new one as it lands. It does not need 2007.

**The historical record** feeds §29 step 11 (the announcement → publication
lead-time distribution) and leakage control in any Level 2 backtest. That is
where the sixteen modeling-era batch starts are needed.

Splitting these means the site's calibration blocker is much smaller than "build
sixteen years of history" — and, unhelpfully, that it is currently blocked on an
announcement that has not been made rather than on research.

## Sources — what works

Tested directly.

| source | reachable | gives an announcement date? |
|---|---|---|
| shonenjump.com official お知らせ | **yes, via WebFetch** | yes — the date is in the URL path |
| Comic Natalie | live 403 (AWS WAF); **archived** in Wayback | yes, to the minute |
| Oricon / MANTAN / ITmedia ねとらぼ / Dengeki | yes | yes — article timestamps |
| ja.wikipedia (already in `data/raw/sources/`) | local | partial — refs carry dates |
| jajanken.net (already in `data/raw/jajanken/`) | local | **no** |
| hunter.noihjp.com | yes | **no** |

Three findings worth carrying forward:

**README limitation 2 is wrong about Shueisha, for one tool.** shonenjump.com
returns 403 to `curl` but WebFetch retrieves it fine. Its notice URLs encode the
publication date — `/j/2022/10/11/221011_oshirase001.html` — so the announcement
date comes free with the URL. This is the closest thing to a primary source the
project has: it is the publisher announcing, on the publisher's own site, dated.

**Natalie is the systematic source for the historical era, through Wayback.**
Live requests hit an AWS WAF challenge, but the CDX API plus a raw
(`…/TIMESTAMPid_/…`) fetch returns the article with its own byline timestamp —
「2011年8月1日 0:00」 for the 2011 return. Comic Natalie has covered every HxH
return since 2011 and its article IDs are discoverable by search. Note: the
Internet Archive was returning "Temporarily Offline" at the end of this session,
so the route is proven but was not usable to finish the sweep.

**jajanken cannot help, and that is worth knowing.** The issue pages we already
hold carry the table of contents and the ranking table but no 次号予告 — the
next-issue preview is not in the index. The source that carries our issue
calendar cannot carry our announcement dates.

## What was found — eight of sixteen batch starts

Confirmed: I fetched the source and read the date on it.
Reported: it appears in search results, consistently, but I did not open the
source. Both are recorded here as found; neither has been written to `data/`.

| ch. | published | announced | lead | mechanism | source | status |
|---|---|---|---|---|---|---|
| 311 | 2011-08-08 | 2011-08-01 00:00 | **7 d** | WSJ 2011 #34, on sale that day | Comic Natalie 53978 (Wayback 20111125234850) | confirmed |
| 341 | 2014-06-02 | — | | | | not found |
| 350 | 2016-04-18 | 2016-03-19 | ~30 d | WSJ 2016 #16 | Natalie 180376, ねとらぼ 3253064 | reported |
| 361 | 2017-06-26 | 2017-05-31 00:01 | 26 d | WSJ official site | MANTAN 20170531dog00m200000000c | confirmed |
| 371 | 2018-01-29 | 2017-12-04 | **56 d** | WSJ 2018 #1, on sale that day | ねとらぼ 3273715 | confirmed |
| 381 | 2018-09-24 | — | | | | not found |
| 391 | 2022-10-24 | 2022-10-11 | 13 d | shonenjump.com お知らせ | shonenjump.com/j/2022/10/11/ | confirmed |
| 401 | 2024-10-07 | 2024-08-19 | 49 d | Jump PRESS (YouTube) | Natalie 587187 | reported |
| 411 | 2026-06-29 | 2026-06-22 00:00 | **7 d** | WSJ next-issue preview | Oricon 2399405, Dengeki 73331 | confirmed |

Still missing: **261, 271, 281, 291, 301, 321, 331, 341, 381** — nine of
sixteen. The 2007–2012 cluster is the hard part; Comic Natalie's coverage of the
series does not obviously reach back to the 2007 and 2008 returns, and no
substitute with reliable timestamps has surfaced yet.

Announcements that are not returns also belong in the record, because §12 treats
supersession and closure as first-class:

- **2022-12-26**, shonenjump.com 『HUNTER×HUNTER』今後の掲載についてのお知らせ
  — weekly serialization ends with ch. 400; ch. 401 onward continue in a
  non-weekly format. An announcement that *opens* a forecast rather than closing
  one. (The notice body is an image, so only the date is machine-readable.)
- **2023-03-09**, Oricon — the format is still undecided.

## What the eight dates already say

**Lead time is not 7–13 days.** `docs/model.md:179` says "Announcement lead time
is only 7–13 days, so announcements close the forecast only at the very end …
there is no early-warning signal to exploit." The observed leads are **7, 13,
26, 30, 49, 56**. The claim was drawn from too few cases and should not survive.

There are two mechanisms and they are cleanly separated:

    次号予告, the preview in the immediately preceding issue  ->  exactly 7 days
    advance notice — official site, an earlier issue, a Jump
    YouTube programme                                        ->  13 to 56 days

That is not a nuisance. It says an announcement can arrive up to eight weeks
before publication, which is well before the point where the production evidence
has resolved — so there *is* an early-warning signal, and §12's "announcement
timing is itself forecastable" has something to forecast. It also says
P(announcement date) should be a mixture, for the same reason the batch-start
gap prior is one. Two mechanisms, two modes.

The 2024 case is the one that breaks the frame hardest: the return was announced
on a **YouTube programme**, seven weeks out, not in the magazine at all. Any
collection method that only looks at Weekly Shonen Jump will miss it.

**Announcement dates must come from timestamped reporting, never from our issue
calendar.** The 2016 announcement rode WSJ #16. Our calendar gives that issue an
on-sale date of 2016-03-21 by `cover_date − 14 days`; the reporting says
2016-03-19. That is README limitation 1 — the inferred on-sale dates for the
1,009 issues with no HxH chapter — feeding straight into the lead-time
distribution if the record derives dates from issues rather than from articles.
Announcement issues are, by definition, issues without a chapter, so they are
exactly the issues whose on-sale dates we have not observed.

There is a by-product here: an announcement dated by a news article *identifies*
the real on-sale date of an issue the calendar only guessed at. The announcement
record can pay back into `wsj_issues.csv`.

**Source reporting disagrees, so the record needs adjudication.** For the 2026
return Oricon names issue #29 and everyone else names #30; our calendar puts #30
on sale 2026-06-22, which matches the article timestamps. The announcement
*date* is solid at 2026-06-22; the issue number is not, and §12's schema wants
both. `docs/tweet_corpus.md` already warns that aggregators carry a "411–420
announced" claim Togashi's own post contradicts. Expect to arbitrate.

## Suggested next steps

1. **Separate the files.** `announcements.csv` is a live schedule stub that
   `build_posterior.py` reads by length; rename it to say so, and give the
   historical record its own file with the full §12 schema (announcement date,
   chapters, issue, single-vs-batch, supersedes, source URL, source type,
   retrieval timestamp, confidence).
2. **Fix `docs/model.md:179`** — the 7–13 day claim is contradicted by the 26,
   30, 49 and 56-day observations above.
3. **Finish the modern era first** (2011 onward, eight of nine already located)
   via Wayback + Natalie, once the Internet Archive is back up. It is enough to
   estimate the lead-time distribution, and it covers every batch the production
   corpus can speak to.
4. **Treat 2007–2010 as a separate, lower-confidence problem.** Five batch
   starts, no obvious source. Recording them as unknown is honest and does not
   block anything the modern era does not already unblock.
5. **Start recording forward announcements now.** The live §20 split needs the
   next announcement captured on the day it lands, with its timestamp — which is
   a process, not a research task.
