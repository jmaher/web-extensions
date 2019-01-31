import datetime
import json
import os
import time
from thclient import TreeherderClient


PLATFORMS = ['android-em-4-3-armv7-api16',
             'linux32', 'linux64-qr', 'linux64',
             'osx-10-10', 'macosx64-qr', 'macosx64',
             'windows7-32', 'windows10-64-qr', 'windows10-64']

FAILURES = {}


def loadFailures(date):
    global FAILURES

    filename = 'failures-%s.json' % date
    with open(filename, 'r') as f:
        data = json.load(f)
    FAILURES = data


def loadFBCTests(thclient, date, start=0, end=None):
    global FAILURES

    if not FAILURES:
        loadFailures()

    filename = cacheName('fixed_by_commit_testnames-%s.json' % date)
    if os.path.exists(filename):
        with open(filename, 'r') as fHandle:
            data = json.load(fHandle)
        FAILURES['fixed_by_commit_tests'] = data
        return

    testnames = []
    raw_data = {}
    raw_filename = cacheName('raw_fixed_by_commit_testnames.json')
    if os.path.exists(raw_filename):
        with open(raw_filename, 'r') as fHandle:
            raw_data = json.load(fHandle)

    new_failures = False
    for jobid in FAILURES['fixed_by_commit']:
        # load raw failures
        # if testname, save off and store in whitelist database
        if not os.path.exists(raw_filename) or \
           str(jobid[0]) not in raw_data.keys():
            new_failures = True
            print "missing key: %s" % jobid[0]
            failures = thclient._get_json('jobs/%s/bug_suggestions' % jobid[0],
                                          project=jobid[1])
            raw_data[str(jobid[0])] = failures
        else:
            failures = raw_data[str(jobid[0])]

        lines = [f['search'].split('|')[1]
                 for f in failures if len(f['search'].split('|')) == 3]

        job_tests = []
        for line in lines:
            name = cleanTest(line.strip())
            if not name or name.strip() == '':
                continue

            # ignore generic messages
            if name in ['automation.py']:
                continue

            # ignore talos tests for fixed by commit
            # TODO: make this more complete
            if name in ['damp', 'tp5n', 'tp5o', 'about_preferences_basic']:
                continue

            # we find that unique failures that exist already is all we need
            if name not in testnames and name in FAILURES.keys():
                job_tests.append(name)

        testnames.extend(job_tests[start:end])

    with open(filename, 'wb') as f:
        json.dump(testnames, f)
    if not os.path.exists(raw_filename) or new_failures:
        with open(raw_filename, 'wb') as f:
            json.dump(raw_data, f)
    FAILURES['fixed_by_commit_tests'] = testnames


def cacheName(filename):
    return "cache/%s" % filename


def loadFailureLines(thclient, jobs, branch, revision, force=False):
    retVal = []

    filename = cacheName('%s-%s-jobs.json' % (branch, revision))
    if not force and os.path.exists(filename):
        try:
            with open(filename, 'r') as fHandle:
                data = json.load(fHandle)
            return data
        except json.decoder.JSONDecodeError:
            pass

    for job in jobs:
        # get bug_suggestions, not available via client, so doing a raw query
        failures = thclient._get_json('jobs/%s/bug_suggestions' % job['id'],
                                      project='autoland')
        lines = [f['search'] for f in failures]
        job['failure_lines'] = lines
        retVal.append(job)

    with open(filename, 'wb') as f:
        json.dump(retVal, f)

    return retVal


def loadAllJobs(thclient, branch, revision):
    filename = cacheName("%s-%s.json" % (branch, revision))
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    pushes = thclient.get_pushes(branch, revision=revision)
    retVal = []
    for push in pushes:
        done = False
        count = 2000
        offset = 0
        while not done:
            jobs = thclient.get_jobs(branch,
                                     push_id=push['id'],
                                     count=count,
                                     offset=offset)
            for job in jobs:
                retVal.append(cleanConfigs(job))

            if len(jobs) == count:
                offset += count
            else:
                done = True
    with open(filename, 'wb') as f:
        json.dump(retVal, f)
    return retVal


def filterJobsByName(alljobs, jtname):
    retVal = []
    for job in alljobs:
        # TODO: find proper name, fix this
        if job['job_type_name'] == jtname:
            continue
        retVal.append(job)
    return retVal


def filterFailedJobs(alljobs):
    retVal = []
    for job in alljobs:
        if job['result'] == 'success':
            continue
        retVal.append(job)
    return retVal


def filterRegressions(alljobs):
    retVal = []
    for job in alljobs:
        if job['result'] == 'success':
            continue
        if job['failure_classification_id'] != 2:
            continue
        if job not in retVal:
            retVal.append(job)
    return retVal


def cleanConfigs(job):
    platform = job['platform']
    config = job['platform_option']

    if config == 'pgo':
        config = 'opt'

    if platform.startswith('macosx64'):
        platform = platform.replace('macosx64', 'osx-10-10')

    job['config'] = config
    job['platform'] = platform
    return job


def cleanTest(testname):
    try:
        testname = str(testname)
    except UnicodeEncodeError:
        return ''

    if testname.startswith('pid:'):
        return ''

    if ' == ' in testname or ' != ' in testname:
        if ' != ' in testname:
            left, right = testname.split(' != ')
        elif ' == ' in testname:
            left, right = testname.split(' == ')

        if 'tests/layout/' in left and 'tests/layout/' in right:
            left = 'layout%s' % left.split('tests/layout')[1]
            right = 'layout%s' % right.split('tests/layout')[1]
        elif 'build/tests/reftest/tests/' in left and \
             'build/tests/reftest/tests/' in right:
            left = '%s' % left.split('build/tests/reftest/tests/')[1]
            right = '%s' % right.split('build/tests/reftest/tests/')[1]
        elif testname.startswith('http://10.0'):
            left = '/tests/'.join(left.split('/tests/')[1:])
            right = '/tests/'.join(right.split('/tests/')[1:])
        testname = "%s == %s" % (left, right)

    if 'build/tests/reftest/tests/' in testname:
        testname = testname.split('build/tests/reftest/tests/')[1]

    if 'jsreftest.html' in testname:
        testname = testname.split('test=')[1]

    if testname.startswith('http://10.0'):
        testname = '/tests/'.join(testname.split('/tests/')[1:])

    # http://localhost:50462/1545303666006/4/41276-1.html
    if testname.startswith('http://localhost:'):
        parts = testname.split('/')
        testname = parts[-1]

    if " (finished)" in testname:
        testname = testname.split(" (finished)")[0]

    # TODO: does this affect anything?
    if testname in ['Main app process exited normally',
                    None,
                    'Last test finished',
                    '(SimpleTest/TestRunner.js)']:
        return ''

    testname = testname.strip()
    testname = testname.replace('\\', '/')
    return testname


# TODO: make this more optimized, this is called everytime,
#       maybe cache the results of repeated jobs?
# if there is >2 data points and >=50% are green, ignore it
def repeatSuccessJobs(failedjob, allJobs):
    matched_jobs = filterJobsByName(allJobs, failedjob['job_type_name'])
    success = len([x for x in matched_jobs if x['result'] == 'success'])
    if success + len(matched_jobs) < 2:
        return 0.5
    return (success / len(matched_jobs))


def analyzeGreyZone(list, max_failures=3):
    bad_items = []
    pmap = {}
    for item in list:
        key = item[0]  # platform
        if key not in pmap.keys():
            pmap[key] = []

        if item[3] not in pmap[key]:
            pmap[key].append(item[3])

        if len(pmap[key]) >= max_failures:
            bad_items.extend([x for x in pmap[key] if x not in bad_items])
    return bad_items


def analyzeFrequentFailures(list, max_failures=3):
    bad_items = []
    pmap = {}
    for item in list:
        key = item[2]  # testname
        if key not in pmap.keys():
            pmap[key] = []

        if item[3] not in pmap[key]:
            pmap[key].append(item[3])

        if len(pmap[key]) >= max_failures:
            bad_items.extend([x for x in pmap[key] if x not in bad_items])
    return bad_items


def analyzeSimilarFailures(list, max_failures=3):
    bad_items = []
    pmap = {}
    for item in list:
        key = item[2]  # testname
        # strip the leafname and look for directory
        parts = key.split('/')
        if len(parts) > 1:
            key = '/'.join(parts[:-1])

        if key not in pmap.keys():
            pmap[key] = []

        if item[3] not in pmap[key]:
            pmap[key].append(item[3])

        if len(pmap[key]) >= max_failures:
            bad_items.extend([x for x in pmap[key] if x not in bad_items])
    return bad_items


def filterLowestCommonClassification(results):
    """
      For all testfailures identified, ensure jobs are not marked as
      intermittent if there is another reason not to by rewriting
      classification

      TODO: we should adjust confidence, need to revisit
    """

    # classification priority
    high = ['newfailure', 'unknown']

    uniqueids = []
    for id in [x[3] for x in results]:
        if id not in uniqueids:
            uniqueids.append(id)

    # for each job, find all tests, identify 'high' classifications
    for id in uniqueids:
        matches = [x for x in results if x[3] == id]
        highvalue = [x[3] for x in matches if x[5] in high]
        # if no high confidence or only 1 failure, ignore
        if len(highvalue) == 0 or len(matches) == 1:
            continue

        # rewrite classification to append '-low'
        for x in results:
            if x[3] == id:
                x[5] = "%s-low" % x[5]

    return results


def analyzeJobs(jobs, alljobs):
    '''
        Currently sheriffs look at a task and annotate the first test failure
        99% of the time ignoring the rest of the failures.  Here we analyze
        all failures for a given task which result in more unknowns.
        As a solution we will ignore failures that:
         * are known infra or leak warnings
         * > 5 lines (only look at first 5 lines)
         * traceback, harness/mozharness messages
         * assertions

        Unlike the sheriffs we will be looking only at a single commit, not
        taking into account similar failures on previous or future commits,
        nor knowing history of intermittents.  We will have access to 14 days
        of test failures and 30 days of regressions so we have a reference set
        to use in order to provide a classification for each job.

        We will parse each line looking for a 'testname', I will ignore the
        specific failure.

        Given the testname, we will store results for a job in a tuple of:
        [platform, config, testname, jid, jobname, classification, confidence]

        Classification severity should be:
          * unknown (0) - default
          * infra (1)
          * leak (2)
          * intermittent (3)
          * newfailure (4)
          * previousregression (5)
          * regression (6)

        Confidence will be based on factors such as repeated runs, a known
        regression from the past, and frequency across platform and the entire
        push.

        As this is intended to run in real time, we will sometime categorize
        an orange as intermittent but then on future results we will find
        frequency of the failure and could mark it as a regression or unknown.

        When done analyzing a job, we will classify all failures and then
        pick the highest failure classification for the job.  The intended
        consumers of this api will be:
          * push health in treeherder (per test analysis, not per job)
          * meta analysis over time (matching results to sheriff annotations)
          * potentially altering default view of orange jobs in treeherder

        Because the consumers are a wide variety, I want to ensure we provide
        accurate information related to both per test failure and per job
        failure.
    '''
    infra = ['raptor-main TEST-UNEXPECTED-FAIL: no raptor test results were found',
             'Uncaught exception: Traceback (most recent call last):']
    ignore_leaks = ['tab missing output line for total leaks!',
                    'plugin missing output line for total leaks!',
                    'process() called before end of test suite']

    ignore = ['[taskcluster:error]',
              'Return code:',
              'ABORT',
              'Received SIGINT (control-C), so stopped run',
              'Uncaught exception:',
              '/builds/worker/workspace/mozharness/mozharness/base/script.py',
              'self.run_action',
              'self._possibly_run_method',
              'Automation Error:',
              'The mochitest suite:',
              'TBPL FAILURE',
              'Assertion failure:',
              'AsyncShutdown timeout',
              'Force-terminating active process',
              'InvalidArgumentException:',
              'JavascriptException:',
              'ChunkedEncodingError:',
              'No suite end',
              'Logged with data',
              'No tests run',
              'HTTP Error 500',
              'runjunit.py',
              'runtests.py',
              'No such file or directory',
              'not a valid structured log message',
              'timed out loading test page:',  # raptor
              'Error copying results',
              'exception output:',
              'zombiecheck',
              'shutil error:',
              'mozdevice.adb.ADBTimeoutError:',
              'ValueError: invalid literal for int() with base 10:',
              'timed out after']

    results = []
    for job in jobs:
        job_results = []

        for line in job['failure_lines'][:5]:
            result = [job['platform'],
                      job['config'],
                      '',
                      job['id'],
                      job['job_type_name'],
                      "unknown",             # classificaiton
                      50]                    # confidence

            # android and wpt have unicode characters embedded in many cases
            line = line.encode('ascii', 'ignore')
            testname = line.strip()
            # format: "TEST-UNEXPECTED-FAIL | <name> | <msg>"
            parts = line.split('|')
            if len(parts) == 3:
                testname = cleanTest(parts[1].strip())
                if parts[2].strip() in ignore_leaks:
                    result[5] = 'leak'
                if parts[2].strip() in ignore:
                    result[5] = 'infra'
            elif len(parts) == 2:
                # not a formatted error
                continue

            if [x for x in ignore if len(testname.split(x)) > 1]:
                break
            if not testname or testname == '':
                continue

            result[2] = testname

            if parts[0].strip() == 'PROCESS-CRASH':
                result[5] = 'intermittent'
                job_results.append(result)
                break
            elif (testname in infra):  # and not len(job_results) == 0:
                # TODO: figure out a solution for timeouts/hang on start
                result[5] = 'infra'
            elif testname in ['leakcheck', 'LeakSanitizer', 'ShutdownLeaks']:
                # TODO: figure out a solution for leaks, they happen A LOT
                result[5] = 'leak'
            elif testname in FAILURES.keys():
                result[5] = 'intermittent'
                if job['platform'] in FAILURES[testname].keys():
                    result[6] = 75
                    platform = FAILURES[testname][job['platform']]
                    if job['config'] in platform.keys():
                        result[6] = 100
            else:
                result[5] = 'newfailure'

            result[6] = repeatSuccessJobs(job, alljobs) * 100

            # Not perfect, could have intermittent that is cause of fbc
            if testname in FAILURES['fixed_by_commit_tests']:
                result[5] = 'previousregression'

            # TODO: if there is >1 failure for platforms/config, increase pct
            # TODO: if >1 failures in the same dir or platform, increase pct

            # TODO: how many unique regression in win7*reftest*
            # Marking all win7 reftest failures as int, too many font issues
            if job['platform'] == 'windows7-32' and \
                ('opt-reftest' in job['job_type_name'] or
                 'debug-reftest' in job['job_type_name']):
                result[5] = 'intermittent'
                result[6] = 50

            job_results.append(result)

        # if job has no results (i.e. all infra), mark as intermittent
        if len(job_results) == 0:
            job_results.append([job['platform'],
                                job['config'],
                                job['job_type_name'],
                                job['id'],
                                job['job_type_name'],
                                'infra',
                                50])

        results.extend(job_results)

    # filter out jobs that have new/unknown to mark all related job changes
    results = filterLowestCommonClassification(results)

    # TODO: this is sort of hacky, but it safeguards many regressions
    max_failures = 3
    if len(jobs) <= 15:
        max_failures = 2
    if len(jobs) <= 5:
        max_failures = 1

    unknown_ids = []
    for type in ['leak', 'infra']:
        jids = [x for x in results if x[5] == type]
        rv = analyzeGreyZone(jids, max_failures=max_failures)
        unknown_ids.extend([x for x in rv if x not in unknown_ids])

    rv = analyzeFrequentFailures(results, max_failures=max_failures)
    unknown_ids.extend([x for x in rv if x not in unknown_ids])

    rv = analyzeSimilarFailures(results, max_failures=max_failures)
    unknown_ids.extend([x for x in rv if x not in unknown_ids])

    temp = []
    for item in results:
        if item[3] in unknown_ids:
            item[5] = 'unknown'  # TODO: is this right?  retriggers?
        if item not in temp:
            temp.append(item)
    return temp


def analyzePush(client, branch, push, verbose=False):
    jobs = loadAllJobs(client, branch, push['revision'])

    # find failed jobs, not tier-3, not blue(retry), just testfailed
    failed_jobs = filterFailedJobs(jobs)
#    failed_jobs = [j for j in failed_jobs if j['tier'] != 3]
    failed_jobs = [j for j in failed_jobs if j['tier'] == 1]
    failed_jobs = [j for j in failed_jobs if j['result'] == 'testfailed']

    # temporarily filter out test-verify/builds
    filtered = []
    for job in failed_jobs:
        if job['job_type_name'].startswith('build') or \
           job['job_type_name'].startswith('repackage') or \
           job['job_type_name'].startswith('hazard') or \
           job['job_type_name'].startswith('spidermonkey') or \
           job['job_type_name'].startswith('valgrind') or \
           len(job['job_type_name'].split('test-verify')) > 1:
            continue
        filtered.append(job)
    failed_jobs = filtered
    failed_jobs = loadFailureLines(client,
                                   failed_jobs,
                                   branch,
                                   push['revision'])

    # get list of fixed_by_commit jobs
    regressed_jobs = filterRegressions(jobs)
    regressed_ids = []
    for x in regressed_jobs:
        if x['id'] not in regressed_ids:
            regressed_ids.append(x['id'])
    regressed_ids = [x['id'] for x in regressed_jobs]

    oranges = analyzeJobs(failed_jobs, jobs)
    orange_ids = [x[3] for x in oranges
                  if x[5] in ['infra', 'leak', 'intermittent']]

    # TODO: what about no data, typically in: talos/raptor/android

    # failed_jobs - oranges - regressions == missed
    missed = [x for x in failed_jobs if x['id'] not in orange_ids]
    missed = [x for x in missed if x['id'] not in regressed_ids]
    bad_classified = [x for x in regressed_jobs if x['id'] in orange_ids]

    if verbose and len(bad_classified) > 0:
        print push['revision']
        print "  failed: %s" % len(failed_jobs)
        print "  oranges: %s" % len(oranges)
        print "  missed: %s" % len(missed)
        for job in missed:
            tests = ["%s" % (x[2]) for x in oranges if job['id'] == x[3]]
            print "    %s (%s)" % (job['job_type_name'], tests)
        print "  known regressions: %s" % len(regressed_jobs)

        print "  BAD CLASSIFY: %s" % len(bad_classified)
        for job in bad_classified:
            tests = ["%s" % (x[2]) for x in oranges if job['id'] == x[3]]
            print "    %s (%s)" % (job['job_type_name'], tests)
        print ""

    return {'regressed_push': int(len(regressed_jobs) > 0),
            'failed': len(failed_jobs),
            'oranges': len(oranges),
            'regressed_jobs': len(regressed_jobs),
            'missed_jobs': len(missed),
            'missed_push': int(len(missed) > 0),
            'bad_jobs': len(bad_classified),
            'bad_push': int(len(bad_classified) > 0)}


def getPushes(client, branch, date):
    parts = date.split('-')
    d = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]))
    start_date = time.mktime(d.timetuple())
    end_date = start_date + 86400

    filename = cacheName('pushes-%s.json' % date)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            pushes = json.load(f)
    else:
        pushes = client.get_pushes(branch,
                                   count=1000,
                                   push_timestamp__gte=start_date,
                                   push_timestamp__lte=end_date)
        with open(filename, 'wb') as f:
            json.dump(pushes, f)

    return pushes


client = TreeherderClient(server_url='https://treeherder.mozilla.org')
branch = 'autoland'
dates = ['2019-01-15', '2019-01-16', '2019-01-17', '2019-01-18', '2019-01-19']

for iter in range(15, 29):
    date = '2019-01-%s' % iter
    pushes = getPushes(client, branch, date)
    loadFailures(date)
    loadFBCTests(client, date)

    total = {'regressed_push': 0,
             'failed': 0,
             'oranges': 0,
             'regressed_jobs': 0,
             'missed_jobs': 0,
             'missed_push': 0,
             'bad_jobs': 0,
             'bad_push': 0}

    for push in pushes:
        results = analyzePush(client, branch, push, verbose=False)
        for item in results.keys():
            total[item] += results[item]

    print "%s: %s (%s), %s (%s) - failed: %s (%s)" % (date,
                                                      total['bad_push'],
                                                      total['bad_jobs'],
                                                      total['missed_push'],
                                                      total['missed_jobs'],
                                                      len(pushes),
                                                      total['failed'])
