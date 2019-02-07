In order to filter out a lot of noise in the intermittent tests, we need to have historical data to reference.  This exists in 2 forms:
 * testnames and related configurations for the last 14 days
 * specific testnames that are annotated as fixed_by_commit

# Testnames of previous failures
For the testnames and related configurations, I currently query active data for tests that have failed in the last 14 days.  This is a big list and I include the platform and configuration we run on.  This gets stored in a data structure:
```
[{testname:
    {platform1:
      {config1: count,
       config2: count},
     platform 2:
      {config1: count}},
 {testname2:
    {platform1:
      {config1: count,
       config2: count},
     platform 2:
      {config1: count}}
]
```

In this case there are some parameters to understand here:
 * testname*: this is name of the test (failure_line sanitized), a string
 * platform*: this is the name of the platform we run on (linux64, windows7-32, windows10-64, etc.).  There is some sanitization here.  I only have platforms listed if there was a failure on the platform, therefore a given list of platforms for a test != all possible platforms.
 * config*: this is the config we use (i.e. opt, debug) and this is slightly sanitized to simplify our configs.  Just like platform, we only list a config if there are failures found while running on that config.
 * count: number of occurances we have failures for this specific testname/platform/config (not used currently)

How this data is used is that for all new failures that are seen, we find the testname and if it matches a testname in our data, then we say there is 50% confidence that we have a known intermittent.  If the platform matches, we increase the confidence to 75%, and finally if the config matches the confidence is at 100%.

Some caveats here:
 * this isn't the failure message, but the testname.  In many cases a test can fail for different reasons (bad value vs timeout) and we ignore that
 * there are many assumptions made in sanitizing test names, for example we run some tests with a file: or http: prefix, most are just a path
 * we do not care about bugs or other annotations, only the raw failures


# Testnames of fixed_by_commit failures
The second type of data we care about is previous regressions found.  Often we backout code for failing a test and in many cases the same test will find multiple regressions (sometimes the same patch).  In playing with this data we fond that previous regression data was needed for >14 days, and analyzing many regressions it became clear that the large majority of regressions that showed up again happened within 30 days.

Here we currently query active data for tests that failed but have failure_classification=2 (fixed_by_commit).  This produces a much smaller list than the overall failures, but keep in mind that this is a subset of the original failures.

This data is stored in an array:
```
[testname1, testname2, testname3, etc.]
```

In order to get the testnames, we actually do a 2 pass query:
 * query activedata for jobids that have failure_classification=2
 * query treeherder for the failure_lines for the matching jobids

Given the failure lines, we apply the same sanitization that we do for the failure testnames and remove duplicates.

These testnames are used when we have a failure we are trying to match we first see if the 'testname' in fixed_by_commit_testnames array and if so, classify it as a previous regression which would mean we need more data.


