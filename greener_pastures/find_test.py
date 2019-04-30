import json

filename = 'failures-2019-02-05.json'
testname = 'dom/canvas/test/test_invalid_mime_type_blob.html'
#testname = 'dom/tests/mochitest/dom-level1-core/test_hc_attrclonenode1.html'

with open(filename, 'r') as f:
    data = json.load(f)

if testname in data.keys():
    print "found testname"
    print data[testname]

