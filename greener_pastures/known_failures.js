/*
	This web extension takes a known set of historical
    failures (as failures.json) which has platform, config,
    and testname- then marks jobs as green if current
    failures are found in the known failure list.
*/

// Hack to take a job name and output a platform and config
// mild sanitization goes on here
//
function parseJobname(jobname) {
    if (jobname.indexOf('test-') == 0) {
        jobname = jobname.substring(5, (jobname.length))
    }

    let parts = jobname.split('/');
    let platform = parts[0];
    let config = parts[1];
    let ispgo = platform.indexOf('-pgo');
    if (ispgo != -1)
        platform = platform.substring(0,ispgo);

    config = config.split('-')[0]

    let isasan = platform.indexOf('asan');
    if (isasan != -1) {
        platform = platform.substring(0,isasan);
        config = 'asan';
    }
    if (platform == 'macosx64') {
        platform = 'osx-10-10';
    }

    return [platform, config];
}

// a testname (TEST-FAIL | <testname> | reason) is what we key off of
// do some mild sanitization here
//
function cleanTest(testname) {
    // TODO: split out remote and file paths, specifically in reftest
    if (testname.indexOf(' == ') != -1) {
        left, right = testname.split(' == ')
        if (left.indexOf('tests/layout/') != -1)
            left = 'layout' + left.split('tests/layout')[1]
        if (right.indexOf('tests/layout/') != -1)
            right = 'layout' + right.split('tests/layout')[1]
        return left + " == " + right;
    }

    // http://localhost:50462/1545303666006/4/41276-1.html
    if (testname.indexOf('http://localhost:') == 0) {
        parts = testname.split('/');
        return parts[parts.length-1];
    }
    return testname
}

window.onload = async function() {
	console.log('loaded');
};

var checkExist = setInterval(function() {
	revnodes = document.querySelectorAll('span .revision-list')
	if (revnodes.length >= 1) {
		// Calculate success rate for SETA and display
		analyzeFailedTests();
	} else {
		console.log("Not found...")
	}
}, 100);

async function analyzeFailedTests() {
    await fetch(browser.runtime.getURL("failures.json"))
      .then(function(response) {
        return response.json();
      })
      .then(function(knownFailures) {
        var jobs = document.querySelectorAll('.btn-orange-classified');
        jobs.forEach(function(job) {
          let attrs = job.attributes;
          let jobid = 0;
          let title = '';
          for(var i = attrs.length - 1; i >= 0; i--) {
            if (attrs[i].name == 'data-job-id')
              jobid = attrs[i].value;
            if (attrs[i].name == 'title')
              title = attrs[i].value.split(' ')[2]
          }
          if (jobid == 0 || title == '')
            return;

          // https://treeherder.mozilla.org/api/project/mozilla-inbound/jobs/219013973/bug_suggestions/
          fetch('https://treeherder.mozilla.org/api/project/mozilla-inbound/jobs/' + jobid + '/bug_suggestions/')
            .then(function(response) {
                response.json().then(function(failJson) {
                  failJson.forEach(function(failure) {
                    // TODO: find failures that have test names
                    let parts = failure.search.split('|');
                    if (parts.length == 3) {
                      testname = cleanTest(parts[1].trim());
                      if (testname == 'leakcheck')
                        return
                      if (testname == 'Main app process exited normally')
                        return
                    } else {
                      // ignore these, usually chain reaction messages or unrelated
                      return
                    }

                    // parse title (plaform,config) and testname and match with knownFailures
                    let platconf = parseJobname(title);
                    let platform = platconf[0];
                    let config = platconf[1];
                    if (typeof knownFailures[testname] !== 'undefined' &&
                        typeof knownFailures[testname][platform] !== 'undefined' &&
                        typeof knownFailures[testname][platform][config] !== 'undefined') {
                      job.className = job.className.replace(/btn-orange-classified/, "btn-green");
                      //TODO: keep track of names for toggling
                    } else {
                      console.log("BAD: '" + testname + "'");
                    }
                  })
                })
            });
        })
    });
}
