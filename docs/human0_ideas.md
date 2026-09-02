## 1. human0 profile
This section is for AI agents better knowing the human collaborator. This may help agents decide how to communicate and document more efficiently.
1. human0 is a phd in a small area within earth sciences. She has the basic training in mathematics and statistics. 
2. human0 has some experience with coding and a lot of experience with scientific research.
3. human0 hasn't been trained in a software production environment.

## 2. ideas on the forecast model
1. Level 1 model is to estimate a prior. I wonder if it's fair to compare different estimation methods by using the final outcomes. My understanding is that prior distribution is usually arbitrary or comes from something outside statistics, like the background knowledge. 
2. I feel recency weighting is a must for Level 1, although the data seems not speak for it. The dataset is very small.
3. Level 2 model is crucial for the final predictions. I have an idea for defining the random variables.

	I think the chapter production, including chapter, chapter position in the batch, production stage, and status, can be encoded as one random variable. I'll call it *C* here for now. 
	The production of a chapter has a series of stages and it's almost linear. 

Here is my design. Correct me if I am wrong with the stages. Suggest a better design if you have an idea. 

| Stage               | numbers to be added          | cumulative increment | Note                                                                                                                                                                              | Example: for Chapter 405, C =                                       |
| ------------------- | ---------------------------- | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| page_completion     | 0.01 per page                | 0.19                 | There are usually 19 pages per chapter. In a tweet, if Togashi shows multiple pages, assume he has finished all the pages before and include the largest number                   | 404.6 means Togashi has completed sketching 6 pages of this chapter |
| panel_layout        | 0.11                         | 0.3                  | Togashi doesn't tweet every single stage or every single page. When he skips, assume previous stages have been completed already.                                                 | 404.3                                                               |
| character_inking    | 0.2                          | 0.5                  |                                                                                                                                                                                   | 404.5                                                               |
| bg_spec             | 0.1                          | 0.6                  |                                                                                                                                                                                   | 404.6                                                               |
| bg_work             | 0.1                          | 0.7                  |                                                                                                                                                                                   | 404.7                                                               |
| dialogue            | 0.1                          | 0.8                  |                                                                                                                                                                                   | 404.8                                                               |
| manuscript_complete | 0.1                          | 0.9                  |                                                                                                                                                                                   | 404.9                                                               |
| retouch             | 0.09                         | 0.99                 | this is the nonlinear part. I assume the retouch won't take too long to the final completion. So it only adds a small number the manuscript_complete and won't subtract anything. | 404.99                                                              |
| published           | round up the nearest integer |                      |                                                                                                                                                                                   | 405                                                                 |

This way, the distance, *d*, between production stages of different chapters can be easily defined as
	*d_ij = C_i - C_j*
Here, since we are only interested in the first chapter of the next (or a further) chapter, *C_i* is always an integer. *C_j* can be in the same batch or a past batch, so *d_ij* can be negative. Meanwhile, each production event and publication date has its timestamp *t_i*. So the time interval between events can be similarly defined as
	*t_ij = t_i - t_j*

The goal is to estimate the probabilities of the publication date for the 1st chapter of a future batch by analyzing the statistical relationship between *d_ij* and the *t_ij*. 
4. I want to expand the definition of d_ij and t_ij above. C_i and C_j are now interchangeable. They can be any chapter coordinates. So do t_i and t_j, they can be any chapter coordinates. For example, C_i = 415.9, C_j = 407.18, and the distance between them is d_ij = 8.62. This distance can be between a page log event (407.18) and a manuscript completion (415.9) of different chapters in different batch. So this approach is like plotting a variogram cloud and maybe fit with a variogram model. We will have a lot more data points for the predictions instead of 3 batches for analog.