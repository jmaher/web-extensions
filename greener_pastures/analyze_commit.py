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


def loadFailureLines(jobs, branch, revision):
    retVal = []

    filename = '%s-%s-jobs.json' % (branch, revision)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    # https://treeherder.mozilla.org/api/project/mozilla-central/jobs/<id>/bug_suggestions/
    for job in jobs:
        # get bug_suggestions, not available via client, so doing a raw query
        failures = client._get_json('jobs/%s/bug_suggestions' % job['id'], project='autoland')
        lines = [f['search'] for f in failures]
        job['failure_lines'] = lines
        retVal.append(job)

    with open(filename, 'wb') as f:
        json.dump(retVal, f)

    return retVal


def loadAllJobs(branch, revision):
    filename = "%s-%s.json" % (branch, revision)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return data

    # https://treeherder.mozilla.org/api/project/mozilla-central/resultset/?full=true&count=10&revision=1db2248f4415
    pushes = client.get_pushes(branch, revision=revision) # gets last 10 by default
    retVal = []
    for push in pushes:
        # https://treeherder.mozilla.org/api/project/mozilla-central/jobs/?return_type=list&count=2000&push_id=424356
        done = False
        count = 2000
        offset = 0
        while not done:
            jobs = client.get_jobs(branch, push_id=push['id'], count=count, offset=offset)
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
    # TODO: split out remote and file paths, specifically in reftest
    testname = str(testname)
    if ' == ' in testname:
        left, right = testname.split(' == ')
        if 'tests/layout/' in left:
            left = 'layout%s' % left.split('tests/layout')[1]
        if 'tests/layout/' in right:
            right = 'layout%s' % right.split('tests/layout')[1]
        return "%s == %s" % (left, right)

    # http://localhost:50462/1545303666006/4/41276-1.html
    if testname.startswith('http://localhost:'):
        parts = testname.split('/')
        return parts[-1]
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
                testname = cleanTest(parts[1].strip());
                if testname == 'leakcheck' and parts[2].strip() in ignore_leaks:
                    continue
                if testname == 'Main app process exited normally':
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

            # TODO: if there is >1 test failure across platforms/config, increase pct
            # TODO: if there are a collection of failures in the same dir or platform, increase pct
            oranges.append([job['platform'], job['config'], testname, job['id'], pct])

    # TODO:
    # remove bad_infra, bad_leaks, regressions
#    oranges = removeOranges(oranges, analyzeGreyZone(infra, max_failures=3))
#    oranges = removeOranges(oranges, analyzeGreyZone(leaks, max_failures=3))
#    oranges = removeOranges(oranges, analyzeFrequentFailures(oranges, max_failures=3))
    return oranges


def removeOranges(oranges, toremove):
    removing = []
    for item in toremove:
        removing = [o for o in oranges if o[3] == item]
        oranges = [o for o in oranges if not o[3] == item]
    return oranges
        

branch = 'autoland'
revisions = ['b3c8a3a052ea']
loadFailures()
client = TreeherderClient(server_url='https://treeherder.mozilla.org')

for revision in revisions:
    jobs = loadAllJobs(branch, revision)
    failed_jobs = filterFailedJobs(jobs)
    failed_jobs = loadFailureLines(failed_jobs, branch, revision)
    oranges = analyzeJobs(failed_jobs, jobs)
    orange_ids = [x[3] for x in oranges]
    regressed_jobs = filterRegressions(jobs)
    missed = [x for x in failed_jobs if x['id'] not in orange_ids]
    print "failed: %s" % len(failed_jobs)
    print "oranges: %s" % len(oranges)
    print "missed: %s" % len(missed)
    print "known regressions: %s" % len(regressed_jobs)
    bad_classified = [x for x in regressed_jobs if x['id'] in orange_ids]
    print "BAD CLASSIFY: %s" % len(bad_classified)
    for bad in bad_classified:
        print bad['job_type_name']
