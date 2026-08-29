# Togashi / Hunter × Hunter Chapter Forecasting Project

## 1. Project Overview

This project aims to build a quantitative forecasting system for the release of future
Hunter × Hunter chapters using:

1. Historical chapter publication records.
2. Yoshihiro Togashi's public X posts documenting manuscript-production progress.
3. Bayesian updating to incorporate new production information as it becomes available.
4. A primary forecast of the Weekly Shonen Jump publication week/issue in which the
   next Hunter × Hunter publication batch will begin.
5. A conditional forecast of the subsequent chapters in the batch once the batch-start
   distribution is estimated.
6. Secondary forecasts for individual production milestones, such as estimated inking
   completion, dialogue completion, manuscript completion, and delivery to Shonen Jump.
7. A future community forecasting system in which fans can make probabilistic predictions
   about important future plot events.

The project should initially be treated as a forecasting/research project rather than
a monetization project.

The central question is:

> Given everything that was publicly known at time t, what probability distribution
> should we assign to the release dates of the next Hunter × Hunter chapters?

---

# 2. Core Statistical Idea

The initial statistical model should combine two sources of information.

### Historical publication behavior

Historical chapter publication records establish the baseline probability distribution.

This represents:

> "If we knew nothing about the current production status, what would historical
> publication behavior suggest?"

This distribution is the **prior**.

### Togashi's production updates

Togashi's tweets provide new information about the current state of chapter production.

Examples include:

- inking completed
- background specifications completed
- dialogue completed
- manuscript completed
- manuscript delivered to Shonen Jump
- other explicitly reported production milestones

These observations provide the **evidence/likelihood** used to update the prior.

Conceptually:

    Prior × Likelihood → Posterior

or:

    P(release date | current evidence)
      ∝
    P(current evidence | release date)
      ×
    P(release date)

The result should be a posterior predictive distribution rather than a single predicted
date.

The final predictions become - 
> Given everything that was publicly known at time t, what probability distribution
> should we assign to the Weekly Shonen Jump issue/week in which the next Hunter × Hunter publication batch will begin?

The primary prediction target is the publication week or Weekly Shonen Jump issue,
rather than an arbitrary calendar date.

Calendar dates may be displayed to users as a convenient representation, but the
underlying model should operate on the actual publication schedule and issue calendar.

---

# 3.  Primary Prediction Target: Next Batch Start

Hunter × Hunter is often published in batches.

Therefore, the next 10 chapters should NOT initially be modeled as ten completely
independent release-date predictions.

The primary prediction target is:

    W_b = publication week or Weekly Shonen Jump issue in which batch b begins.

The primary model estimates:

    P(W_b | all information available at time t)

rather than directly predicting an arbitrary calendar date.

The next Hunter × Hunter publication batch may contain multiple consecutive chapters.
Therefore, the main statistical uncertainty is usually:

> When will the next batch begin publication?

Once the batch-start issue is known or estimated, the publication dates of subsequent
chapters may be highly constrained by the within-batch publication schedule.

For example:

    Batch begins
        ↓
    Chapter N
        ↓
    Chapter N+1
        ↓
    Chapter N+2
        ↓
    ...
        ↓
    Chapter N+9

The model should therefore distinguish:

### Batch-start uncertainty

Probability distribution for when the next batch begins.

### Within-batch schedule

Conditional distribution of subsequent chapter release dates given the batch start.

If the publication schedule makes a subsequent chapter effectively deterministic
conditional on the batch schedule, its conditional probability can be very close to 1.

Do NOT automatically represent such chapters as having literal 100% probability.
Instead use language such as:

> "Near-certain conditional on the estimated batch schedule."

Uncertainty in the batch-start week propagates to every subsequent chapter in the batch, even when the within-batch schedule is nearly deterministic.

## Definition of a batch

A batch is a **run of consecutive Weekly Shonen Jump issues** carrying Hunter ×
Hunter chapters. A new batch begins when issues elapse without a chapter.

Two decisions fix this definition. Both were taken after inspecting the
historical record and are recorded in `docs/batch_segmentation.md`.

### Runs longer than a normal batch are split into 10-chapter units

Historically almost every batch is 9 to 11 chapters, but two runs are much
longer: chapters 291–310 (20 chapters) and 311–340 (30 chapters). These are
treated as **back-to-back 10-chapter batches published with no waiting time**,
not as single oversized batches.

    chapters 291-310  ->  two batches of 10, gap between them = 0 issues
    chapters 311-340  ->  three batches of 10, gaps between them = 0 issues

Runs of 9 or 11 chapters are left intact. Only runs materially longer than a
normal batch are split.

This has a real consequence for the model, and it is intended: the
batch-to-batch gap distribution now contains **zeros**. It becomes bimodal —
either the next batch follows immediately, or it follows after a long hiatus.
The model must represent this as a mixture rather than as a single unimodal gap
distribution.

### Batch size is treated as approximately constant

Batch size is not modeled as a random quantity in the initial model. Splitting
long runs into 10-chapter units makes 10 the working batch size, which keeps the
model simple and the conditional ten-chapter forecast tractable.

Revisit this only if backtesting shows batch-size variation is materially hurting
forecasts.

---
# 4. Weekly Shonen Jump Publication Calendar

The model should use the actual Weekly Shonen Jump publication/issue calendar rather
than assuming that every calendar week is an available publication week.

The publication calendar may include:

- regular weekly issues
- combined issues
- holiday breaks
- weeks without a regular issue

The model should therefore predict the next eligible Weekly Shonen Jump publication
issue/week.

Calendar dates should be derived from the issue calendar for display purposes.

The historical publication dataset should record the issue/week associated with every
Hunter × Hunter chapter whenever possible.

---
# 5. Historical Publication Dataset

Construct a canonical historical publication dataset.

At minimum include:

- chapter number
- publication date
- Weekly Shonen Jump issue/date
- batch identifier
- position within batch
- previous chapter publication date
- interval from previous chapter
- previous batch publication date
- interval from previous batch
- known publication gaps
- hiatus periods
- known scheduled breaks
- announcement date, where the publication was announced in advance
- announcement source
- whether the chapter was announced or unannounced at any given time
- source URL
- source type
- retrieval date

Where possible, distinguish:

- chapter publication date
- issue release date
- announcement date
- manuscript completion date

Do not conflate these events.

The announcement date is the date the announcement became **public**. It is a
separate event from the publication it announces, and recording it correctly is
what makes leakage-free backtesting possible.

---

# 6. Historical Prior

Use historical publication records to construct the baseline prior.

Calculate distributions for:

- chapter-to-chapter publication intervals
- batch-to-batch intervals
- batch sizes
- within-batch intervals
- time between manuscript completion and publication
- other relevant publication intervals

The initial prior should answer:

> What is the probability distribution of the next Weekly Shonen Jump publication
> week/issue in which a Hunter × Hunter batch begins, based solely on historical
> publication behavior?

The prior distribution should initially be represented over discrete candidate
publication issues/weeks rather than continuous calendar dates.

Do not incorporate current Togashi tweets into the historical prior.

This prevents information leakage.

## Modeling era: 2007 onward

Hunter × Hunter has had two clearly different publication regimes.

    1998-2006  weekly serialization with frequent short breaks
    2007-      bursts of consecutive issues separated by long hiatuses

Only the **2007-onward** era (chapter 261 forward) is used to fit the batch-start
prior. The earlier weekly era is a different data-generating process, and
including it would contaminate the prior with intervals that no longer describe
how the series is published.

The 1998–2006 data is **retained, not discarded**. It stays in the canonical
dataset and should be used for:

- descriptive statistics and visualization
- long-run trend analysis
- any question where the weekly era is genuinely the relevant comparison
- checking whether an apparent pattern in the modern era also held earlier

Do not delete it, and do not silently fold it into the prior.

## Recency weighting

The modern era supplies only a small number of batch-start observations, and the
gap behavior may have drifted over time. Recent batches should therefore carry
more weight than older ones when fitting the prior.

Weighting is preferred over fitting an explicit trend or changepoint: with this
few observations, a trend model would overfit, while weighting degrades
gracefully.

Rules:

1. The weighting scheme is a **hyperparameter selected by backtesting**, not by
   intuition. Try several decay rates, including no decay, and choose by
   out-of-sample calibration and sharpness.
2. Report the **effective sample size** alongside any weighted fit. Aggressive
   downweighting can reduce an already small sample to a handful of effective
   observations, which widens the posterior more than it sharpens it.
3. Weights must be computed **as of the forecast timestamp** during backtesting.
   Applying today's weights to a historical forecast is information leakage.

---

# 7. Togashi X Data Collection

Collect Togashi's public X posts, preferably from the primary source.

For every raw post preserve:

- tweet ID
- creation timestamp
- original Japanese text
- URLs
- media information
- conversation/reply information
- retrieval timestamp
- source/API/archive
- any relevant metadata

The raw tweet dataset must be immutable.

Never overwrite the original tweet text.

If an interpretation changes later, modify the processed dataset rather than the raw data.

---

# 8. Processing Tweets Into Production Events

Posts should be transformed into structured production events.

This taxonomy is derived from the corpus, not assumed in advance: 212 text-
bearing sources (189 text posts + 23 milestone texts read off images) plus 218
page-log posts. The canonical Japanese→event mapping lives in
`data/taxonomy/production_events.yaml`; this section defines its shape.

## Events are (stage × status), not a flat list

A flat list of completion types cannot express the things Togashi actually
reports — starts, blocked waits, and rework. Every chapter-scoped event is
therefore a **stage** plus a **status**.

Togashi described his own pipeline on 2024-09-24:

    アナログで人物ペン入れ   analog character inking
          ↓
    アナログで背景          analog backgrounds
          ↓
    デジタルで背景・効果・装飾  digital backgrounds, effects, decoration
          ↓
    プリントアウト原稿に加筆   touch-ups on the printed manuscript

Canonical stages, in pipeline order:

| stage | Japanese seen in corpus | who does it |
|---|---|---|
| `name` | ネーム | Togashi |
| `character_inking` | 人物ペン入れ, ペン入れ | Togashi |
| `bg_spec` | 背景指定書作成, 背景効果指定, 指定作成 | Togashi |
| `bg_work` | 背景, 背景効果 | staff |
| `dialogue` | 台詞入れ, 台詞清書, フキダシ内の台詞清書 | Togashi |
| `retouch` | 加筆, 最終加筆 | Togashi |
| `manuscript_complete` | 原稿完成, 完成 | Togashi |

Statuses:

| status | Japanese | meaning |
|---|---|---|
| `started` | 開始 | work on this stage began |
| `in_progress` | 中, 進行中 | ongoing |
| `complete` | 完了, 完成, 終了 | stage finished |
| `awaiting_return` | 返却待ち | **blocked on staff**, not progress |
| `under_review` | 確認中 | with the editor |
| `retake` | リテイク | rework ordered; regresses the chapter |

**Synonyms are era-dependent and must be mapped, not matched literally.** The
2022 posts say 台詞清書 and 背景効果指定; the 2024–26 posts say 台詞入れ and
背景指定書作成 for the same stages. A literal-string extractor will silently lose
the entire 2022 era.

## Non-chapter event classes

These carry real forecasting signal and have no place in a chapter-stage schema:

| class | example | why it matters |
|---|---|---|
| `page_completed` | page log: ch 417, pages 13,14 | a production **rate**, ~218 observations; see `docs/production_page_log.md` |
| `batch_countdown` | 「取り敢えず、次はあと8話。」 | direct statement of chapters remaining in a batch |
| `batch_scope` | 「10話分の指定が完了しました」 | a stage completed across a whole batch at once |
| `disruption` | 「No.424の原稿捜索中。」 (manuscript lost); illness; workspace moves | explains silences that are not slow progress |
| `ancillary_work` | 単行本, 表紙, カラー, commissioned illustrations | competes for the same hours as chapter production |

`page_completed` is the highest-volume evidence in the corpus by an order of
magnitude. Any design that treats production evidence as sparse milestones is
throwing away most of the data.

## Rules the extractor must obey

**1. One post can yield many events.** Up to 8 chapters have been reported in a
single post, and a post may carry both a milestone and a page log (2025-11-10
reads 「No.426 ペン入れ 開始!」 *and* shows manuscript page 1). Event extraction is
one-to-many, and `image_type` must be a set, not a single value.

**2. State is not monotonic.** リテイク sends a chapter backwards, sometimes after
`manuscript_complete`. The model tracks a chapter's current state; a later event
may *regress* it. Never assume a stage, once complete, stays complete.

**3. Work is not strictly sequential across chapters.** On 2024-11-08, mid-way
through drawing ch 424, Togashi posted 「No.408、加筆完了」. Chapters receive work
long after their pages are drawn, so events for a chapter may arrive in any order
relative to other chapters.

**4. Waiting is not progress.** `awaiting_return` means he is blocked on staff.
Time in that state behaves differently from time he is drawing, and conflating
them will mis-estimate throughput.

**5. Chapter numbers need a plausibility check.** Togashi mistypes his own
(「No388.399…完成」 where 388 should be 398). Reject or flag a chapter number
outside the plausible open range.

## Every event record retains

- chapter number (or `null` for batch/disruption/ancillary events)
- stage, status, event class
- event date, and the post's creation timestamp
- tweet ID and source URL
- the **verbatim Japanese** the event was derived from
- extraction method: `text_explicit`, `image_transcription`, or `inferred`
- confidence
- interpretation notes

Keep explicit and inferred events separate.

Never infer a production event without recording that it is an inference.

An event read from an image is an **interpretation of a photograph**, not a text
quote, and must be marked as such — with the human confirmation status carried
alongside (see `data/annotations/review_queue.csv`).

---

# 9. Production-to-Publication Intervals

For every historical chapter for which both a production event and publication date
are known, calculate the interval between the production event and publication.

Examples:

    inking completion → publication

    dialogue completion → publication

    background specification completion → publication

    manuscript completion → publication

    delivery to Shonen Jump → publication

For each stage, preserve the individual observations.

Do not reduce the information to a single average.

For example:

    T_inking_to_release

should be represented as an empirical distribution rather than merely:

    mean(T_inking_to_release)

Initially inspect:

- mean
- median
- variance
- quantiles
- skewness
- outliers
- multimodality
- temporal trends
- chapter-position effects
- batch effects

Do not assume a normal distribution without checking.

---

# 10. Bayesian Updating

The historical publication process provides the prior distribution for the publication
week/issue in which the next Hunter × Hunter batch will begin.

Every new Togashi production tweet provides new information that should update this
distribution.

The primary posterior of interest is:

    P(next batch start week | historical publication data, all Togashi evidence observed so far)

or:

    P(W_b | H, E_1, E_2, ..., E_t)

where:

- W_b is the next batch-start publication week/issue
- H is historical publication information
- E_1 ... E_t are all production observations available up to time t

Each new Togashi tweet should be treated as sequential evidence about the timing of the next batch.

The model does not discard earlier observations when a later production milestone is
reported.

Instead, the posterior after one observation becomes the prior for the next update.

P(W_b | H)
        ↓
observe E_1
        ↓
P(W_b | H, E_1)
        ↓
observe E_2
        ↓
P(W_b | H, E_1, E_2)
        ↓
observe E_3
        ↓
P(W_b | H, E_1, E_2, E_3)

The system should therefore support sequential Bayesian updating.

---
# 11. Sequential Evidence and Dependence Between Tweets

Every new Togashi production tweet should be used as new evidence for updating the
forecast of the next batch-start week.

Earlier observations should NOT be discarded simply because a later production milestone
is observed.

For example:

    Dialogue completed
            ↓
    Posterior P(W_b | dialogue completed)
            ↓
    Manuscript completed
            ↓
    Updated posterior P(W_b | dialogue completed, manuscript completed)

The earlier dialogue-completion observation remains part of the available information.

However, production milestones are not statistically independent.

For example:

    dialogue completed

and:

    manuscript completed

are related observations because manuscript completion generally occurs after dialogue
completion.

Therefore, the model should not blindly assume:

    P(E_1, E_2 | W_b)
        =
    P(E_1 | W_b) × P(E_2 | W_b)

unless independence is justified by the data.

Instead, sequential updating should conceptually use:

    P(W_b | E_1, E_2)
        ∝
    P(E_2 | W_b, E_1) × P(W_b | E_1)

The posterior after the earlier observation becomes the prior for the later observation.

In practical implementations, the dependence between production stages can be handled
by modeling the current production state, the sequence of production events, or the
conditional time remaining after each stage.

The key rule is:

> Every new tweet updates the forecast, but the model must account for the fact that
> later production observations are related to earlier observations.

Do not discard earlier tweets.
Do not treat correlated production stages as completely independent evidence.

---

# 12. Publisher Announcements

Shueisha announces upcoming Hunter × Hunter publication in advance — in Weekly
Shonen Jump itself, on the official Shonen Jump site, and through Jump editorial
channels. An announcement may name a single issue or an entire batch.

A publisher announcement is a **different class of information** from a Togashi
production tweet, and the model must not treat the two the same way.

    Togashi tweet          ->  probabilistic evidence about production state
    Publisher announcement ->  a publication date, stated in advance

## Announcements are treated as real publication dates

An announced publication date is treated as a real publication date that happens
to lie in the future. It is scheduling information, not a noisy signal about
manuscript progress.

It therefore does NOT enter the likelihood as another observation to be weighed
against the prior. It settles the question the prior was estimating.

## Announcement closes the affected predictions

When the publisher announces the issue in which a chapter will appear, the
forecast for that chapter **closes**.

    chapter forecast open
            |
    publisher announces issue
            |
    forecast closes; chapter recorded as scheduled

A closed prediction:

- leaves the set of open forecasts
- is no longer updated by subsequent production tweets
- records the announcement timestamp and source
- keeps every forecast snapshot generated before it closed

Closing is not retroactive. The forecasts made before the announcement remain in
the record exactly as they were, and remain scored. See the Forecast Evolution
and Historical Forecast Visualization sections — an announcement is one of the
most important annotations on the probability history, because it is usually the
moment a distribution collapses.

## Announced does not mean immutable

Announced schedules can change. Hiatuses have been extended and issues moved.

Consistent with the rule against literal 100% probabilities, a closed prediction
is recorded as **scheduled**, not as certain. If a later announcement contradicts
an earlier one:

- retain both announcements with their timestamps
- reopen the affected prediction
- record the reopening as an event in the forecast history

Do not silently overwrite a superseded announcement.

## What remains to be forecast after an announcement

An announcement rarely closes everything. Typically still open:

- chapters beyond the announced horizon
- the size of the current batch, if not stated
- the start of the *next* batch
- all production milestones for unannounced chapters

The primary forecast target moves forward accordingly. When the current batch is
fully announced, the live target becomes the start of the following batch.

## Announcement timing is itself forecastable

Because announcements are so informative, *when the announcement will arrive* is
a useful secondary forecast in its own right:

    P(announcement date | current production evidence)

The historical lead time between announcement and publication should be measured
and preserved as an empirical distribution, exactly as production-stage intervals
are.

## Record every announcement

For each announcement retain:

- announcement date (when it became public)
- announced chapter number(s)
- announced issue/week
- whether it names a single chapter or a batch
- whether it supersedes an earlier announcement
- source URL
- source type
- retrieval timestamp
- confidence

The announcement date and the publication date are separate events and must not
be conflated.

## Leakage warning

Announcements are the single largest hindsight-bias risk in this project. A
backtest that can see an announcement before it was public will look extremely
accurate and will be worthless.

Every announcement must carry the timestamp at which it became public, and
historical forecasts must use only announcements available at or before the
forecast timestamp. See the Prevent Hindsight Bias section.

---

# 13. Recommended Initial Model

The initial model should be organized into three levels.

## Level 1 — Historical Batch-Start Prior

Use historical publication records to estimate:

    P(W_b | historical publication data)

where W_b is the Weekly Shonen Jump publication week/issue in which the next batch begins.

This is the baseline prior.

## Level 2 — Production Evidence Model

Process every available Togashi production tweet into structured evidence.

Examples include:

- chapter number
- production stage
- event date
- sequence of events
- time since previous milestone
- number of chapters at each production stage

Use this information to estimate how the current overall production state affects the
probability distribution of the next batch-start week.

The model should update sequentially as new tweets arrive.

## Level 3 — Conditional Within-Batch Schedule

Conditional on the estimated batch-start week, estimate the release weeks of subsequent
chapters in the batch.

This may have relatively low uncertainty if the within-batch schedule is historically
regular.

The uncertainty in the batch-start prediction must still propagate to all subsequent
chapter predictions.

## Level 0 — Announced Schedule

Before any of the three levels run, check whether the publisher has already
announced the publication in question.

    announced?  --yes-->  prediction closes; chapter recorded as scheduled
        |
        no
        |
    Level 1 -> Level 2 -> Level 3

Level 0 overrides the statistical model. It is not combined with it, not weighed
against it, and not used to shift a prior. An announced chapter is scheduled, and
the model's job moves on to whatever is still unannounced.

Only announcements public at or before the forecast timestamp may be consulted.
---

# 14. Secondary Production Forecasts

In addition to the primary forecast of the next batch-start week, the system should
generate forecasts for intermediate production milestones.

Examples include:

- estimated inking completion date for a newly started chapter
- estimated dialogue completion date
- estimated manuscript completion date
- estimated delivery date to Shonen Jump
- estimated remaining time at the current production stage
- estimated date of the next publisher announcement

The announcement forecast is worth singling out. Because an announcement closes
the primary prediction, forecasting *when it will arrive* is effectively
forecasting when the uncertainty will be resolved — useful to readers, and a
sharp test of the production model, since announcement timing should itself be
predictable from production state.

For example, if a chapter's dialogue completion is reported, the system may estimate:

    P(delivery date | dialogue completed)

Likewise, if a chapter has just entered production, the system may estimate:

    P(inking completion date | current production information)

These secondary forecasts serve two purposes:

1. They provide interesting and useful information for users.
2. They help evaluate and understand the production-process model that ultimately
   informs the primary batch-start forecast.

Secondary forecasts should also be probabilistic and should report distributions or
credible intervals rather than only point estimates.

---

# 15.  Conditional Ten-Chapter Forecast

The primary statistical prediction is the publication week/issue in which the next batch
begins.

The forecast for the next 10 chapters is a derived, conditional forecast.

For each possible batch-start week:

    batch start = W_b
        ↓
    apply the estimated within-batch publication schedule
        ↓
    derive release-week distributions for subsequent chapters

The final prediction for each chapter must incorporate uncertainty in:

1. the batch-start week
2. the within-batch publication schedule
3. possible publication breaks or irregularities

For every chapter report:

- median predicted release date
- 50% credible interval
- 80% credible interval
- 90% credible interval
- probability of release by selected dates
- estimated batch membership
- conditional uncertainty

Example:

| Chapter | Median | 50% interval | 80% interval | 90% interval |
|---|---|---|---|---|
| N+1 | date | range | range | range |
| N+2 | date | range | range | range |
| ... | ... | ... | ... | ... |
| N+10 | date | range | range | range |

The forecast should provide a probability distribution rather than only one date.

---

# 16. Forecast Evolution

The site should preserve every forecast generated by the model.

For example:

    August 1 forecast
    August 5 forecast
    August 12 forecast
    August 20 forecast
    August 26 forecast

This allows us to visualize how new information changes the prediction.

When Togashi posts a new production update:

    new tweet
        ↓
    process event
        ↓
    update posterior
        ↓
    generate new 10-chapter forecast
        ↓
    save forecast snapshot

When the publisher announces a schedule:

    announcement
        ↓
    record announcement with its public timestamp
        ↓
    close the affected predictions
        ↓
    save a final snapshot marking them scheduled
        ↓
    move the live target to what is still unannounced

The historical forecast snapshots must never be overwritten.

Closing a prediction does not remove it from the record. Its full probability
history stays visible, and the announcement is the annotation that explains why
the distribution collapsed.

---
# 17. Historical Forecast Visualization

Historical predictions are a core feature of the project.

The website should preserve and visualize how probability distributions changed over time
as new information became available.

This feature is conceptually similar to observing the historical price movement of a
prediction market.

For every forecast timestamp, preserve the full probability distribution over candidate
next batch-start weeks.

The website should visualize:

- probability of each candidate publication week over time
- changes in the median or most likely publication week
- changes in credible intervals
- major probability shifts
- annotations corresponding to new Togashi production tweets
- eventual resolution when the batch begins publication

Example:

    Aug 1  — initial forecast
    Aug 8  — Chapter 425 inking completed
    Aug 15 — Chapter 425 dialogue completed
    Aug 22 — Chapter 426 manuscript completed
    Aug 29 — new production update
    Sep X  — batch officially begins

The visualization should allow users to observe how each new piece of information
changed the model's beliefs. 
Historical forecasts must never be overwritten after the outcome becomes known.

---
# 18. Backtesting

Backtesting is essential.

For each historical date:

1. Pretend that the current date is that historical date.
2. Use only information that was available on or before that date.
3. Generate a 10-chapter forecast.
4. Record the forecast.
5. Compare the forecast with what actually happened.
6. Move forward to the next historical forecast date.

This produces a realistic simulation of how the model would have performed in real time.

---

# 19. Prevent Hindsight Bias

This is a critical project rule.

When producing a historical forecast, the model must NOT use:

- future tweets
- future publication dates
- **future publisher announcements**
- later corrections
- future production milestones
- future batch-size information
- information that was not publicly available at the forecast timestamp

Publisher announcements deserve particular care. They are far more informative
than any other observation, so a leaked announcement will make a backtest look
excellent while telling you nothing about the model. Any backtest whose accuracy
jumps sharply should be checked for announcement leakage before it is believed.

Every observation should have a timestamp indicating when it became available.

For announcements this means the date the announcement became **public**, which
is not the date of the issue it appeared in and not the date it was added to any
dataset.

The project must be able to reproduce:

> "What did we know on date T?"

---

# 20. Model Evaluation

Evaluate both accuracy and probabilistic calibration.

Possible metrics:

### Point forecast

- median absolute error
- mean absolute error

### Interval forecast

- 50% interval coverage
- 80% interval coverage
- 90% interval coverage
- interval width

### Probabilistic forecast

- log score
- CRPS
- Brier score for binary/cumulative events

A good probabilistic model should be both:

### Calibrated

Events assigned 70% probability should occur approximately 70% of the time.

### Sharp

The model should avoid unnecessarily wide probability distributions.

A model that predicts extremely wide intervals for everything is not necessarily useful.

## Score pre-announcement and post-announcement forecasts separately

A forecast made after the publisher has announced the date is correct for a
trivial reason. Mixing those into the metrics would inflate every score and hide
whether the model has any skill at all.

Partition every evaluation:

    pre-announcement forecasts   ->  the real measure of model skill
    post-announcement forecasts  ->  reported separately, or excluded

**Headline calibration, sharpness, and skill numbers must be computed on the
pre-announcement subset.** Any comparison between the baseline model and the
Bayesian production model must also use only pre-announcement forecasts, or the
comparison measures announcement timing rather than predictive value.

Report the pre-announcement sample size alongside the metrics. It will be much
smaller than the total forecast count, and that is the number that matters.

---

# 21. Model Comparison

At minimum compare:

## Baseline Model

Historical publication records only.

    Historical publication data
            ↓
        Forecast

## Bayesian Production Model

Historical publication records + Togashi progress data.

    Historical publication data
            +
    Togashi production evidence
            ↓
        Bayesian update
            ↓
        Forecast

The central scientific question is:

> How much predictive information do Togashi's production tweets add beyond historical
> publication behavior?

This should be measured through backtesting.

---

# 22. Phase 2 — Community Forecasting

Once Phase 1 is reliable, develop a forecasting community.

The community should be more than a conventional forum.

The primary interaction should be **making predictions about important future story events**.

Examples:

- Will Hisoka die before Chapter 435?
- Will Kurapika form an alliance with Chrollo during the Succession War Arc?
- Will a particular character survive the Succession War?
- Will a particular relationship or alliance occur?
- Will a particular unresolved plot point be revealed by a specified chapter?

Each prediction should have:

- clearly defined outcome
- closing condition/date/chapter
- objective resolution criteria
- probability estimate
- prediction history
- discussion/reasoning
- final outcome

---

# 23. Start With Reputation/Points Rather Than Money

Initially, community predictions should preferably use points or reputation rather than
real-money betting.

Users can build a forecasting record.

Possible metrics:

- prediction accuracy
- Brier score
- calibration
- log score
- prediction streaks
- total resolved predictions
- confidence-weighted accuracy

This creates an incentive to make well-calibrated forecasts rather than simply make
popular guesses.

A user could eventually develop a reputation as:

> One of the best Hunter × Hunter forecasters.

---

# 24. Model vs. Community

Eventually compare:

    Statistical model
        vs.
    Community consensus
        vs.
    Individual forecasters

For example:

    Model:       42%
    Community:   58%

Store the complete probability history.

When the event resolves, evaluate all forecasts.

This creates a second research question:

> Can a statistical production/publication model outperform collective fandom
> forecasting for objective release events?

And:

> Can collective fandom forecasting predict future narrative events better than
> individual forecasters?

---

# 25. Potential Long-Term Vision

If Phase 1 becomes successful, the project could evolve from an H×H release-date
forecasting site into a broader forecasting platform.

Potential layers:

### Layer 1

Hunter × Hunter release forecasting.

### Layer 2

Community prediction of future story events.

### Layer 3

Historical forecasting records and calibration.

### Layer 4

Other manga/serialized media.

The broader concept is:

> Quantitative forecasting of serialized creative works using production signals and
> collective intelligence.

Do not optimize for this expansion prematurely.

First make the H×H forecasting model excellent.

---

# 26. Agent Roles

AI agents may divide the work into the following roles.

## Research Agent

Responsible for:

- finding primary Togashi posts
- finding authoritative publication records
- documenting sources
- identifying relevant secondary archives
- tracking publisher announcements and establishing the date each became public
- detecting when an announcement supersedes an earlier one

## Tweet Extraction Agent

Responsible for:

- extracting raw posts
- identifying chapter numbers
- identifying production events
- preserving original Japanese text

## Validation Agent

Responsible for:

- checking extracted events against source tweets
- detecting ambiguous interpretations
- identifying missing posts
- cross-checking community archives

## Data Agent

Responsible for:

- maintaining canonical datasets
- maintaining schemas
- calculating derived intervals
- preserving provenance
- versioning data

## Statistical Agent

Responsible for:

- constructing the historical prior
- modeling production-stage intervals
- implementing Bayesian updating
- generating predictive distributions
- documenting assumptions

## Backtesting Agent

Responsible for:

- rolling-origin backtesting
- leakage detection
- calibration analysis
- forecast scoring

## Website Agent

Responsible for:

- displaying current forecasts
- displaying uncertainty
- showing historical forecast evolution
- visualizing production progress

## Community Agent

Responsible for Phase 2:

- prediction design
- reputation system
- prediction resolution
- community forecasting metrics

Agents must not silently modify canonical datasets created by other agents.

---

# 27. Data Provenance

Every important observation must be traceable.

For every production event retain:

- source URL
- tweet ID
- source type
- original text
- retrieval timestamp
- interpretation
- confidence
- transformation history

For publication records retain:

- source URL
- publication source
- publication date
- retrieval timestamp
- chapter number
- batch information
- notes

For publisher announcements retain:

- source URL
- announcing body
- date the announcement became public
- announced chapter number(s)
- announced issue/week
- whether it announces a single chapter or a batch
- whether it supersedes an earlier announcement
- retrieval timestamp
- confidence
- notes

A superseded announcement is retained alongside the one that replaced it. Never
overwrite it.

Secondary sources may be used to discover information, but important observations
should be verified against primary sources whenever possible.

---

# 28. Reproducibility

The project should maintain separate layers:

    raw data
        ↓
    cleaned data
        ↓
    structured events
        ↓
    derived features
        ↓
    model inputs
        ↓
    model outputs
        ↓
    forecast snapshots
        ↓
    website

Raw data must never be modified by downstream processing.

Every model result should be reproducible from:

- a specific data version
- a specific model version
- a specific configuration
- a specific forecast timestamp

---

# 29. Initial Development Sequence

Follow this order.

### Phase 1A — Data

1. Build the historical chapter publication dataset.
2. Collect Togashi's historical X posts.
3. Preserve the raw tweet corpus.
4. Create the production-event taxonomy.
5. Convert tweets into structured production events.
6. Validate the extracted events.
6a. Build the historical publisher-announcement record, with the public date of
    each announcement.

### Phase 1B — Statistical Model

7. Calculate historical publication intervals.
8. Apply the batch definition: restrict to 2007 onward, split long runs into
   10-chapter units, treat batch size as approximately constant.
9. Build the historical publication prior, with recency weighting whose decay is
   left as a hyperparameter for Phase 1C to select.
10. Calculate production-stage → publication distributions.
11. Measure the announcement → publication lead-time distribution.
12. Build the first Bayesian updating model, with announcements as a Level 0
    override rather than as likelihood evidence.
13. Generate 10-chapter predictive distributions.

### Phase 1C — Validation

14. Perform rolling-origin backtesting.
15. Test for information leakage, checking announcement timestamps specifically.
16. Compare historical-only vs. historical + Togashi evidence, on
    pre-announcement forecasts only.
17. Evaluate calibration and sharpness, reporting pre- and post-announcement
    forecasts separately.
18. Select the recency-weighting decay by out-of-sample performance.
19. Refine the model only when justified by backtesting.

### Phase 1D — Website

20. Display the current forecast.
21. Display uncertainty intervals.
22. Display production status.
23. Display the announced schedule, and which predictions it has closed.
24. Display historical forecast evolution.
25. Display model performance/calibration.

### Phase 2

26. Introduce community predictions.
27. Introduce reputation/points.
28. Introduce prediction histories.
29. Introduce calibration and forecasting leaderboards.
30. Compare model predictions with community predictions.

---

# 30. Guiding Principle

The project should not aim merely to predict the next chapter correctly.

The goal is to build a system that can answer:

> Given all information available at a specific point in time, how should uncertainty
> about future Hunter × Hunter publication dates be quantified?

The model should be:

- probabilistic
- transparent
- reproducible
- empirically validated
- resistant to hindsight bias
- continuously updated as new information arrives

The ultimate measure of success is **calibration over time**, not an occasional correct
point prediction.