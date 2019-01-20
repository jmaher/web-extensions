import datetime
import json
import os
import re
import sys
import time
from thclient import TreeherderClient


PLATFORMS = ['android-em-4-3-armv7-api16',
             'linux32', 'linux64-qr', 'linux64',
             'osx-10-10', 'macosx64-qr', 'macosx64',
             'windows7-32', 'windows10-64-qr', 'windows10-64']

FAILURES = {}

def loadFailures():
    global FAILURES

    with open('failures.json', 'r') as f:
        data = json.load(f)
    FAILURES = data


def loadFBCTests(thclient):
    global FAILURES

    if not FAILURES:
        loadFailures()

    filename = cacheName('fixed_by_commit_testnames.json')
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)

        testnames = []
        for item in data:
            name = cleanTest(item.strip())
            # ignore generic messages
            if name in ['automation.py']:
                continue

            # ignore talos tests for fixed by commint
            # TODO: make this more complete
            if item in ['damp', 'tp5n', 'tp5o', 'about_preferences_basic']:
                continue

            if name and name not in testnames:
                testnames.append(name)

        FAILURES['fixed_by_commit'] = testnames
        return

    testnames = []
    for jobid in FAILURES['fixed_by_commit']:
        # load raw failures
        # if testname, save off and store in whitelist database
        failures = thclient._get_json('jobs/%s/bug_suggestions' % jobid[0], project=jobid[1])
        lines = [f['search'].split('|')[1] for f in failures if len(f['search'].split('|')) == 3]
        for line in lines:
            name = cleanTest(line.strip())
            # ignore generic messages
            if name in ['automation.py']:
                continue

            # ignore talos tests for fixed by commint
            # TODO: make this more complete
            if item in ['damp', 'tp5n', 'tp5o', 'about_preferences_basic']:
                continue

            if name and name not in testnames:
                testnames.append(name)

    with open(filename, 'wb') as f:
        json.dump(testnames, f)
    FAILURES['fixed_by_commit'] = testnames


def cacheName(filename):
    return "cache/%s" % filename


def loadFailureLines(thclient, jobs, branch, revision):
    retVal = []

    filename = cacheName('%s-%s-jobs.json' % (branch, revision))
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    # https://treeherder.mozilla.org/api/project/mozilla-central/jobs/<id>/bug_suggestions/
    for job in jobs:
        # get bug_suggestions, not available via client, so doing a raw query
        failures = thclient._get_json('jobs/%s/bug_suggestions' % job['id'], project='autoland')
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

    # https://treeherder.mozilla.org/api/project/mozilla-central/resultset/?full=true&count=10&revision=1db2248f4415
    pushes = thclient.get_pushes(branch, revision=revision) # gets last 10 by default
    retVal = []
    for push in pushes:
        # https://treeherder.mozilla.org/api/project/mozilla-central/jobs/?return_type=list&count=2000&push_id=424356
        done = False
        count = 2000
        offset = 0
        while not done:
            jobs = thclient.get_jobs(branch, push_id=push['id'], count=count, offset=offset)
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
    testname = str(testname)

    if testname.startswith('pid:'):
        return ''

    if ' == ' in testname:
        left, right = testname.split(' == ')
        if 'tests/layout/' in left and 'tests/layout/' in right:
            left = 'layout%s' % left.split('tests/layout')[1]
            right = 'layout%s' % right.split('tests/layout')[1]
        elif 'build/tests/reftest/tests/' in left and 'build/tests/reftest/tests/' in right:
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

    # http://localhost:50462/1545303666006/4/41276-1.html
    if testname.startswith('http://localhost:'):
        parts = testname.split('/')
        testname = parts[-1]

    if " (finished)" in testname:
        testname = testname.split(" (finished)")[0]

    if testname in ['Main app process exited normally', 'leakcheck', None, 'ShutdownLeaks', 'Last test finished', '(SimpleTest/TestRunner.js)']:
        return ''

    testname = testname.strip()
    testname = testname.replace('\\', '/')
    return testname


#TODO: make this more optimized, this is called everytime, maybe cache the results of repeated jobs?
# if there is >2 data points and >=50% are green, ignore it
def repeatSuccess(failedjob, allJobs):
    matched_jobs = filterJobsByName(allJobs, failedjob['job_type_name']);
    success = len([x for x in matched_jobs if x['result'] == 'success'])
    return (success / len(matched_jobs))


def analyzeGreyZone(list, max_failures=3):
    bad_items = []
    pmap = {}
    for item in list:
        key = item[0] # platform
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
        key = item[2] # testname
        if key not in pmap.keys():
            pmap[key] = []

        if item[3] not in pmap[key]:
            pmap[key].append(item[3])

        if len(pmap[key]) >= max_failures:
            bad_items.extend([x for x in pmap[key] if x not in bad_items])
    return bad_items


def analyzeJobs(jobs, alljobs):
    infraLines = ['[taskcluster:error] Aborting task...',
                    'raptor-main TEST-UNEXPECTED-FAIL: no raptor test results were found']
    ignore_leaks = ['tab missing output line for total leaks!',
                    'plugin missing output line for total leaks!']

    oranges = []
    leaks = []
    infra = []
    bad_leaks = []
    bad_infra = []
    for job in jobs:
        job_matched = False
        for line in job['failure_lines']:
            parts = line.split('|')
            if len(parts) == 3:
                testname = cleanTest(parts[1].strip())
                if not testname or testname == '':
                    continue
                if parts[2].strip() in ignore_leaks:
                    continue
            elif not job_matched:
                # ignore these, usually chain reaction messages or unrelated
                if line in infraLines:
                   continue

                # for infra issues or other failures, this helps
                repeated = repeatSuccess(job, alljobs)
                if repeated < 0.5:
                    continue
                testname = line.strip()

            pct = 0
            #TODO: figure out a solution for timeouts/hang on start
            if testname in infraLines and not job_matched:
                # if only error (no other lines matched yet), treat as infra
                print "appending: %s" % [job['platform'], job['config'], testname, job['id'], 50]
                infra.append([job['platform'], job['config'], testname, job['id'], 50]);
                pct = 50
            # TODO: figure out a solution for leaks, they happen A LOT
            elif testname in ['leakcheck', 'LeakSanitizer']:
                leaks.append([job['platform'], job['config'], testname, job['id'], 50]);
                pct = 50
            elif testname in FAILURES.keys():
                pct = 50;
                if job['platform'] in FAILURES[testname].keys():
                    pct = 75;
                    if job['config'] in FAILURES[testname][job['platform']].keys():
                        pct = 100;

            repeat = repeatSuccess(job, alljobs) * 100;
            if repeat >= 50:
                pct = repeat
                    
            if pct < 50:
                continue

            if job_matched:
                continue
            job_matched = True

            # Not perfect, could have intermittent that is cause of fbc
            # should we have job_matched = True?
            if testname in FAILURES['fixed_by_commit']:
                continue

            # TODO: if there is >1 test failure across platforms/config, increase pct
            # TODO: if there are a collection of failures in the same dir or platform, increase pct
            oranges.append([job['platform'], job['config'], testname, job['id'], pct])

    # remove bad_infra, bad_leaks, regressions
    leaks = analyzeGreyZone(leaks, max_failures=3)
    infra = analyzeGreyZone(infra, max_failures=3)
    frequent = analyzeFrequentFailures(oranges, max_failures=3)
#    print "oranges: %s, infra: %s, leaks: %s, frequent: %s" % (len(oranges), len(infra), len(leaks), len(frequent))
    oranges = removeOranges(oranges, infra)
    oranges = removeOranges(oranges, leaks)
    oranges = removeOranges(oranges, frequent)
    return oranges


def removeOranges(oranges, toremove):
    removing = []

    for jobid in toremove:
        removing = [o for o in oranges if o[3] == jobid]
        oranges = [o for o in oranges if not o[3] == jobid]
    return oranges
        

client = TreeherderClient(server_url='https://treeherder.mozilla.org')

branch = 'autoland'
revisions = ['b3c8a3a052ea']
loadFailures()
loadFBCTests(client)

filename = cacheName('pushes.json')
if os.path.exists(filename):
    with open(filename, 'r') as f:
        pushes = json.load(f)
else:
    # 2019-01-16 -> 2019-01-17
    # https://treeherder.mozilla.org/api/project/autoland/resultset/?full=true&count=100&push_timestamp__gte=1547596800&push_timestamp__lt=1547767800
    pushes = client.get_pushes(branch, count=1000, push_timestamp__gte=1547596800, push_timestamp__lt=1547767800)
    with open(filename, 'wb') as f:
        json.dump(pushes, f)


total_failed = 0
total_oranges = 0
total_regressedjobs = 0
total_regressedpushes = 0
total_missed = 0
total_missedpushes = 0
total_bad = 0
total_badpushes = 0
for push in pushes:
    jobs = loadAllJobs(client, branch, push['revision'])

    # find failed jobs, not tier-3, not blue(retry), just busted/testfailed
    failed_jobs = filterFailedJobs(jobs)
    failed_jobs = [j for j in failed_jobs if j['tier'] != 3]
    failed_jobs = [j for j in failed_jobs if j['result'] != 'retry']
    failed_jobs = loadFailureLines(client, failed_jobs, branch, push['revision'])

    # get list of fixed_by_commit jobs
    regressed_jobs = filterRegressions(jobs)
    regressed_ids = [x['id'] for x in regressed_jobs]

    oranges = analyzeJobs(failed_jobs, jobs)
    orange_ids = [x[3] for x in oranges]

    # TODO: what about test-verify and builds
    # TODO: what about no data, typically in: talos/raptor/android

    # failed_jobs - oranges - regressions == missed
    missed = [x for x in failed_jobs if x['id'] not in orange_ids]
    missed = [x for x in missed if x['id'] not in regressed_ids]
    # temporarily filter out test-verify/builds
    filtered = []
    for job in missed:
        if job['job_type_name'].startswith('build') or \
           len(job['job_type_name'].split('test-verify')) > 1:
            continue
        filtered.append(job)
    missed = filtered
    bad_classified = [x for x in regressed_jobs if x['id'] in orange_ids]
    total_failed += len(failed_jobs)
    total_oranges += len(oranges)
    total_regressedjobs += len(regressed_jobs)
    if len(regressed_jobs) > 0:
        total_regressedpushes += 1
    total_missed += len(missed)
    if len(missed) > 0:
        total_missedpushes += 1
    total_bad += len(bad_classified)
    if len(bad_classified) > 0:
        total_badpushes += 1

    if len(bad_classified) == 0:
        continue

    print push['revision']
    print "  failed: %s" % len(failed_jobs)
    print "  oranges: %s" % len(oranges)
    print "  missed: %s" % len(missed)
    for job in missed:
        print "    %s" % job['job_type_name']
    print "  known regressions: %s" % len(regressed_jobs)
    for job in regressed_jobs:
        print "    %s" % job['job_type_name']

    print "  BAD CLASSIFY: %s" % len(bad_classified)
    for job in bad_classified:
        print "    %s" % job['job_type_name']
    print ""

print "\n\n"
print "Summary:"
print "  %s pushes" % len(pushes)
print "  %s pushes with regressions" % total_regressedpushes
print "  %s failures" % total_failed
print "  %s classifed" % total_oranges
print "  %s regressed" % total_regressedjobs
print "  %s missed classification" % total_missed
print "  %s pushes with missed" % total_missedpushes
print "  %s bad classifed" % total_bad
print "  %s pushes with bad" % total_badpushes