#!/usr/bin/env python
from argparse import ArgumentParser
import datetime
import json
import os
import sys
import time

import requests

here = os.path.abspath(os.path.dirname(__file__))

ACTIVE_DATA_URL = "https://activedata.allizom.org/query"
TIME_WINDOW = 14


def query_fbc_jobs(end_timestamp=None):
    if not end_timestamp:
        end_timestamp = datetime.datetime.now()
    # TODO: doing this for 30 days results in better results
    start_timestamp = end_timestamp - datetime.timedelta(days=30)

    query = """
{
    "from":"treeherder",
    "select":[
        "job.id",
        "repo.branch.name",
        "build.revision12",
        "failure.notes.text"
    ],
    "where":{"and":[
        {"in":{"repo.branch.name":["mozilla-inbound","autoland","mozilla-central"]}},
        {"gt":{"repo.push.date":{"date":"%s"}}},
        {"lt":{"repo.push.date":{"date":"%s"}}},
        {"regex":{"job.type.name":"test-.*"}},
        {"eq":{"failure.classification":"fixed by commit"}}
    ]},
    "limit":50000
}""" % (start_timestamp.date(), end_timestamp.date())

    response = requests.post(ACTIVE_DATA_URL,
                             data=query,
                             stream=True)
    response.raise_for_status()
    data = response.json()["data"]
    retVal = []
    # build array of jobids
    for counter in range(0, len(data['job.id'])):
        if not data['failure.notes.text'][counter]:
            continue
        if data['failure.notes.text'][counter] == '':
            continue
        if data['job.id'][counter] not in retVal:
            retVal.append([data['job.id'][counter],
                           data['repo.branch.name'][counter],
                           data['build.revision12'][counter]])
    return retVal


def query_activedata_configs(end_timestamp=None):

    if not end_timestamp:
        end_timestamp = datetime.datetime.now()
    last_week = end_timestamp - datetime.timedelta(days=TIME_WINDOW)
    end_timestamp = time.mktime(end_timestamp.timetuple())
    last_week_timestamp = time.mktime(last_week.timetuple())

    query = """
{
    "from":"unittest",
    "groupby":[
        "run.machine.platform",
        "run.type"
    ],
    "limit":200000,
    "where":{"and":[{"gt":{"run.timestamp":%s}},
                    {"lt":{"run.timestamp":%s}},
                    {"neq":{"run.type":"ccov"}},
      {"in":{"repo.branch.name":["mozilla-inbound","autoland","mozilla-central"]}}
    ]}
 }
""" % (last_week_timestamp, end_timestamp)

    response = requests.post(ACTIVE_DATA_URL,
                             data=query,
                             stream=True)
    response.raise_for_status()
    data = response.json()["data"]
    configs = []
    for c in data:
        temp = []
        temp.append(c[0])

        if isinstance(c[1], list):
            if 'e10s' not in c[1]:
                c[1] = ''
            else:
                c[1] = 'e10s'

        if c[1] is None:
            c[1] = ''
        c[1] = c[1].replace('chunked', '')
        temp.append(c[1])
        if c[2] is None:
            temp = []
            continue

        if temp not in configs:
            configs.append(temp)
    return configs


def query_activedata(config, platforms=None, end_timestamp=None):
    config_clause = ''
    if config:
        config_clause = '{"eq":{"run.type":"%s"}},' % config

    # TODO: skip talos, raptor, test-verify, etc.

    if not end_timestamp:
        end_timestamp = datetime.datetime.now()
    last_week = end_timestamp - datetime.timedelta(days=TIME_WINDOW)
    end_timestamp = time.mktime(end_timestamp.timetuple())
    last_week_timestamp = time.mktime(last_week.timetuple())

    # NOTE: we could add build.type to groupby and do fewer queries
    query = """
{
    "from":"unittest",
    "limit":200000,
    "groupby":["result.test", "build.type"],
    "select":[
        {"aggregate":"count","value":"result.ok"},
        {"aggregate":"average","value":"result.duration"}
    ],
    "where":{"and":[
        {"in":{"repo.branch.name":["mozilla-inbound","autoland","mozilla-central"]}},
        {"eq":{"run.machine.platform":"%s"}},
        {"eq":{"result.ok":"F"}},
        %s
        {"gt":{"run.timestamp":%s}},
        {"lt":{"run.timestamp":%s}}
    ]}
}
""" % (platforms, config_clause, last_week_timestamp, end_timestamp)

    response = requests.post(ACTIVE_DATA_URL,
                             data=query,
                             stream=True)
    response.raise_for_status()
    data = response.json()["data"]

    retVal = []
    for test, config, count, runtime in data:
        if isinstance(config, str) or isinstance(config, unicode):
            config = [config]
        if not config or config is None or config == '':
            config = ['opt']

        if 'pgo' in config or 'asan' in config:
            if 'opt' in config:
                config = config.remove('opt')
        elif 'qr' in config:
            config = config.remove('qr')
        elif 'ccov' in config:
            config = config.remove('ccov')

        if config == [None] or not config or len(config) == 0:
            config = ['opt']

        if len(config) != 1:
            print("JMAHER: config too long: %s (%s)" % (config, type(config)))
        retVal.append([test, config[0], count, runtime])

    if len(retVal) == 0:
        print(query)

    return retVal


def write_timecounts(data, config, platform, outdir=here):
    if config:
        platform = "%s-%s" % (platform, config)

    outfilename = os.path.join(outdir, "%s.failures.json" % (platform))
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # consider filtering tests for real test names, not 'automation.py', etc.
    print("writing %s..." % outfilename)
    with open(outfilename, 'w') as f:
            f.write(json.dumps(data, indent=2, sort_keys=True))
    return outfilename


def cli(args=sys.argv[1:]):
    parser = ArgumentParser()
    parser.add_argument('-o', '--output-directory', dest='outdir',
                        default='failures',
                        help="Directory to save runtime data.")
    parser.add_argument('-f', '--from-date', dest='from_date',
                        default=None,
                        help="start date- default:2 weeks prior to --to-date")
    parser.add_argument('-t', '--to-date', dest='to_date',
                        default=None,
                        help="If we want to specify an end date")
    args = parser.parse_args(args)

    # assume format like: 2019-01-15
    if args.to_date:
        parts = args.to_date.split('-')
        args.to_date = datetime.datetime(int(parts[0]),
                                         int(parts[1]),
                                         int(parts[2]))
        dates = [args.to_date]
    else:
        for iter in range(23,32):
            dates.append(datetime.datetime(2018, 12, iter))
        for iter in range(1,32):
            dates.append(datetime.datetime(2019, 1, iter))
        for iter in range(1,20):
            dates.append(datetime.datetime(2019, 2, iter))


    cachedir = args.outdir

    import shutil
    for date in dates:
        print "generated data for date: %s" % date

        if os.path.exists(cachedir):
            shutil.rmtree(cachedir)
        os.mkdir(cachedir)

        # we want to know historical failures that are regressions
        # we can use the job name, revision, jobid to filter them
        fbc = query_fbc_jobs(date)

        configs = query_activedata_configs(date)
        filenames = []
        print("%s configs to test..." % len(configs))
        for config in configs:
            data = query_activedata(config[1], config[0], date)
            if data == []:
                print("no data.....")
                continue

            retfile = write_timecounts(data, config[1], config[0], cachedir)
            filenames.append(retfile)

        failures = {}
        for filename in filenames:
            platform = filename.split(os.sep)[1]
            platform = platform.split('.')[0]
            with open(filename, 'r') as f:
                data = json.load(f)
                for item in data:
                    if item[0] not in failures:
                        failures[item[0]] = {}
                    if platform not in failures[item[0]]:
                        failures[item[0]][platform] = {}
                    if item[1] not in failures[item[0]][platform]:
                        failures[item[0]][platform][item[1]] = 0
                    failures[item[0]][platform][item[1]] += item[2]
        failures['fixed_by_commit'] = fbc

        with open('failures-%s.json' % date.date(), 'w') as f:
            json.dump(failures, f)


if __name__ == "__main__":
    sys.exit(cli())
