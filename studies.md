# Exams

After an exam is done, each character in the exam should have a score recorded into `records` table, with type equals `read` or `write`.

## Write Exam

Endpoint: /exam/generate/write

Characters: From the chosen lessons, filter out characters examed (having "read" or "write" record) in last `days_filter` days. and filter out characters with the last "write" score greater than `score_filter`. Select a random subset.

## Write Review Exam

Endpoint: /exam/generate_review/write

Characters: By SRS schedule, find overdue "write" type cards, select a random subset.

# Studies

After a study is done, each character in the study will be recorded into `records` table, with type equals `readstudy` or `writestudy`. The score will always be 10.

## Generate Study Sheet

Endpoint: /study/generate/chars

If setting "Study source" is set to "basic":

- Characters: From the chosen lessons, filter out characters studied in last `days_filter` days. and filter out characters with the last "read" score greater than `score_filter`. Select a random subset.

If setting "Study source" is set to "review":

- Characters: By SRS schedule, find characters with lowest "Write Retrievability" (exclude 0). Filter out characters studied in last `days_filter` days.

## Find Words Puzzle

Endpoint: /study/generate/words

If setting "Study source" is set to "basic":

Characters: From the chosen lessons, filter out characters examed (having "read" record) in last `days_filter` days. and filter out characters with the last "read" score greater than `score_filter`. Select a random subset.

If setting "Study source" is set to "review":

- Characters: By SRS schedule, find characters with lowest "Read Retrievability" (exclude 0). Filter out characters studied (having "readstudy" record) in last `days_filter` days.

## Cloze test

Endpoint: /study/generate/cloze

If setting "Study source" is set to "basic":

Characters: From the chosen lessons, filter out characters examed (having "read" record) in last `days_filter` days. and filter out characters with the last "read" score greater than `score_filter`. Select a random subset.

If setting "Study source" is set to "review":

- Characters: By SRS schedule, find characters with lowest "Read Retrievability" (exclude 0). Filter out characters studied (having "readstudy" record) in last `days_filter` days.

