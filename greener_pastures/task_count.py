import json

with open('target-tasks.json', 'r') as f:
    data = json.load(f)

print("Total Jobs: %s" % len(data))
print("Total Perf: %s" % len([x for x in data if 'raptor' in x or 'talos' in x]))
print("Total Coverage: %s" % len([x for x in data if 'ccov' in x]))
print("Total Web Platform: %s" % len([x for x in data if 'web-platform-test' in x]))
print("Total Reftest: %s" % len([x for x in data if '-reftest-' in x]))
print("Total hardware: %s" % len([x for x in data if 'android-hw' in x or 'windows10-aarch64' in x or 'windows10-64-ux' in x]))
print("total to skip: %s" % len([x for x in data if 'raptor' in x or 
                                                     'talos' in x or 
                                                     'ccov' in x or 
                                                     'web-platform-test' in x or 
                                                     '-reftest-' in x or 
                                                     'android-hw' in x or 
                                                     'windows10-64-ux' in x or 
                                                     'windows10-aarch64' in x]))
