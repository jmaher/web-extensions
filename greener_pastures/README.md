Greener Pastures is a toolchain to reduce the amount of guesswork (oranges) from a given push by looking at historical failures and classifying real time failure on the target push to be in 1 of two states: unknown, intermittent.

There are a few parts to this:
 * writeruntimes.py - a python script that harvests 2 weeks of historical failure data from activedata and builds a failures.json file
 * analyze_commit.py - a python script that will download push/job/failure information from treeherder and apply heuristics to the failed testcases to give a reasonable conservative classification.
 * known_failures.js - a web extension that loads failures.json (output of writeruntimes.py) and attempts to turn live treeherder oranges to Greener

The web extension is out of date, it was the initial work, but in order to prove accuracy, we needed to scale across a large sample of commits and see if our rules work.  For this exercise so far I have analyzed 814 commits from Jan 15th to 29th.  In this 814 commits, there are 7251 failed jobs and I currently have 40 (0.5%) false positives (this means I mark a job as intermittent, but it was flagged by sheriffs as a regression) and 2805 jobs that are intermittent which are left alone (61.2% success, missing 38.8%)

Obviously I would like to get higher accuracy here, in order to do that a few things need to happen:
 * improved logging, specifically around leaks and infrastructure failures
 * improving the heuristics used- I believe we can profile a push based on total jobs ran to apply different heuristics
 * improve logging for gtest, robocop, marionette, and firefox-ui-test test harnesses
 * consider looking at the base revision- both for improved number of jobs to consider, as well as finding failures that are consistent

Let me explain what data is collected in writeruntimes.py, then what additional data is collected in analyze_commits.py and how we use it.

As mentioned early on, writeruntimes.py collects failures from activedata.  The failures are all failures found on trunk (not try) in the last 14 days on all configs.  Once we collect the data (typically 40+ queries to activedata), we build a structure that looks like:
{ 'testname': {'platformA': {'config1': count, 'config2': count, ...}, 'platformB', {...}}}

In addition to the previous failures for the last 14 days, we also look at jobs that are "fixed by commit" (FBC) which are jobs that failed and we backed out a change as the failure was related to a regression.  We collect 30 days of FBC test data and add it into the failures.json structure like this:
{'fixed_by_commit': [[jobid, branch, revision],[...]]}


The next step is to run analyze_commit.py which will load up failures.json and for the FBC array, we query treeherder for each of the jobs to get the raw failure lines associated with each of the FBC jobs.  We then parse the failure lines to translate them into "testnames" which gives us a clean list of testnames that have caused regressions, this is useful to make sure we know what has caused regressions in the past because often we backout code for a regression more than once.

Now that we have built up a list of failures and the FBC testnames, analyze_commit then downloads a series of pushes (currently by a date such as 2019-01-20) directly from treeherder and for each push the entire list of jobs and their metadata.  