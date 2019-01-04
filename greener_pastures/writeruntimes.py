#!/usr/bin/env python
from argparse import ArgumentParser
from collections import defaultdict
import datetime
import json
import os
import sys
import time

import requests

here = os.path.abspath(os.path.dirname(__file__))

ACTIVE_DATA_URL = "https://activedata.allizom.org/query"
TIME_WINDOW = 14

def query_activedata_configs():

    last_week = datetime.datetime.now() - datetime.timedelta(days=TIME_WINDOW)
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
                    {"neq":{"run.type":"ccov"}},
      {"in":{"repo.branch.name":["mozilla-inbound", "autoland", "mozilla-central"]}}
    ]}
 }
""" % (last_week_timestamp)

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

        if c[1] == None:
            c[1] = ''
        c[1] = c[1].replace('chunked', '')
        temp.append(c[1])
        if c[2] == None:
            temp = []
            continue

        if temp not in configs:
            configs.append(temp)
    return configs

def query_activedata(config, platforms=None):
    config_clause = ''
    if config:
        config_clause = '{"eq":{"run.type":"%s"}},' % config

    # TODO: skip talos, raptor, test-verify, etc.

    last_week = datetime.datetime.now() - datetime.timedelta(days=TIME_WINDOW)
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
        {"gt":{"run.timestamp":%s}}
    ]}
}
""" % (platforms, config_clause, last_week_timestamp)

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
        default=here, help="Directory to save runtime data.")
    args = parser.parse_args(args)

    configs = query_activedata_configs()
    filenames = []
    print("%s configs to test..." % len(configs))
    for config in configs:
        e10s = False
        if config[1] == 'e10s':
            e10s = True
 
        data = query_activedata(config[1], config[0])
        if data == []:
            print("no data.....")
            continue

        filenames.append(write_timecounts(data, config[1], config[0], outdir=args.outdir))

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

    with open('failures.json', 'w') as f:
        json.dump(failures, f)

   
if __name__ == "__main__":
    sys.exit(cli())
