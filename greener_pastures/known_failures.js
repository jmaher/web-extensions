/*
	This web extension takes a known set of historical
    failures (as failures.json) which has platform, config,
    and testname- then marks jobs as green if current
    failures are found in the known failure list.
*/


/* we need to branch/repo because our query for bug suggestions needs
   the repo
*/
function splitRepo(href) {
	var urls = href;
	var myurls = urls.split("?repo=");
	var mylasturls = myurls[1];
	var mynexturls = mylasturls.split("&");
	var url = mynexturls[0];
	return url
};


var completed = false;
let oranges_toggled = [];
var classified_toggled = [];
var missed = [];

var infraLines = ['[taskcluster:error] Aborting task...',
                  'raptor-main TEST-UNEXPECTED-FAIL: no raptor test results were found'];


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
        let parts = testname.split(' == ')
        if (parts[0].indexOf('tests/layout/') != -1)
            parts[0] = 'layout' + parts[0].split('tests/layout')[1]
        if (parts[1].indexOf('tests/layout/') != -1)
            parts[1] = 'layout' + parts[1].split('tests/layout')[1]
        return parts[0] + " == " + parts[1];
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


function toggle_gp() {
    oranges_toggled.forEach(function(item) {
        var job = document.querySelector(item[3]);
        job.className = job.className.replace(/btn-green/, "btn-orange");
    })

    classified_toggled.forEach(function(item) {
        var job = document.querySelector(item[3]);
        job.className = job.className.replace(/btn-green/, "btn-orange-classified");
    })
};


function toggleJobs(list, classified_toggled, oranges_toggled) {
    //TODO: turn leaks orange again
    count = 0
    list.forEach(function (todo_jid) {
        classified_toggled.forEach(function(item) {
            if (item[3] == todo_jid) {
                let jobs = document.querySelectorAll('.gp-classified');
                jobs.forEach(function (job) {
                    let dji = job.attributes.getNamedItem('data-job-id').nodeValue;
                    if (dji == todo_jid) {
                        job.className = job.className.replace(/btn-green gp-classified/, "btn-orange-classified");
                        count++;
                    }
                });
            }
        })
        oranges_toggled.forEach(function(item, pct) {
            if (item[3] == todo_jid) {
                let jobs = document.querySelectorAll('.gp-orange');
                jobs.forEach(function (job) {
                    let dji = job.attributes.getNamedItem('data-job-id').nodeValue;
                    if (dji == todo_jid) {
                        job.className = job.className.replace(/btn-green gp-orange/, "btn-orange");
                        count++;
                    }
                });
            }
        })
    });
    console.log("toggle " + count + " jobs back to orange");
}

function analyzeGreyZone(list) {
    var bad_items = [];
    let pmap = {};
    list.forEach(function (item) {
        let key = item[0];
        if (!(key in pmap)) {
            pmap[key] = [];
        }
        if (pmap[key].indexOf(item[3]) == -1) pmap[key].push(item[3])
        if (pmap[key].length >= 3) {
            pmap[key].forEach(function(jid) {
                if (bad_items.indexOf(jid) == -1) bad_items.push(jid);
            });
        }
    });
    return bad_items;
};


function analyzeFrequentFailures(list) {
    var bad_items = [];
    let pmap = {};
    list.forEach(function (item) {
        let key = item[2];
        if (!(key in pmap)) {
            pmap[key] = [];
        }
        if (pmap[key].indexOf(item[3]) == -1) pmap[key].push(item[3])
        if (pmap[key].length >= 3) {
            pmap[key].forEach(function(jid) {
                if (bad_items.indexOf(jid) == -1) bad_items.push(jid);
            });
        }
    });
    return bad_items;
};


function titleToJobName(title) {
    let jobname = title.split('|')[1];
    jobname = jobname.trim();
    jobname = jobname.split(' ')[0];
    return jobname;
}


//TODO: make this more optimized, this is called everytime, maybe cache the results of repeated jobs?
// if there is >2 data points and >=50% are green, ignore it
function repeatSuccess(failedjob) {
    //get job type and query matching jobs (platform/config/name/chunk)
    let target_title = titleToJobName(failedjob.attributes.getNamedItem('title').nodeValue);
    let jobs = document.querySelectorAll('.job-btn');
    let matched_jobs = [];
    let success = 0;
    jobs.forEach(function (job) {
        let title = titleToJobName(job.attributes.getNamedItem('title').nodeValue);
        if (title == target_title) {
            let status = job.attributes.getNamedItem('title').nodeValue.split('|')[0].trim();
            matched_jobs.push(job);
            if (status == 'success')
                success++;
        }
    });
    return (success / matched_jobs.length);
};


var checkExist = setInterval(function() {
    var navbarElement = document.getElementById("th-global-navbar-top");
	var revnodes = document.querySelectorAll('span .revision-list');
	var inserted_elements_gp = document.getElementById("toggle_gp");
	if (revnodes.length >= 1 && !inserted_elements_gp && !completed) {
		if (!inserted_elements_gp) {
			// Set up the elements
			spanElement = navbarElement.querySelector(".navbar-right");
			spanElement.insertAdjacentHTML("afterbegin",
				`
				<span class='dropdown' style='color:white'>
					<button id='toggle_gp' type='button' title='Toggle known intermittents'
					 class='btn btn-view-nav nav-menu-btn'>
					0 Known Intermittents (Analyzing)
					</button>
				</span>`
			);

			// Save original display settings
			inserted_elements_gp = document.getElementById("toggle_gp");

			// Add onclick functions for success rate initiating
			button_toggle = document.getElementById("toggle_gp");
			button_toggle.addEventListener('click', function() {
				toggle_gp();
			});
            analyzeFailedTests();
        }
	} else if (!completed) {
        analyzeFailedTests();
	} else {
        var status = document.getElementById('toggle_gp')
        status.textContent = status.textContent.replace(/\ \(Analyzing\)/, '');
		console.log("done...");
    }
}, 1000);

async function analyzeFailedTests() {
    await fetch(browser.runtime.getURL("failures.json"))
      .then(function(response) {
        return response.json();
      })
      .then(function(knownFailures) {
        var jobs = document.querySelectorAll('.btn-orange, .btn-orange-classified');
        let oranges_toggled = [];
        let classified_toggled = [];
        let missed = [];
        let leaks = [];
        let infra = []
        console.log("greener pastures has loaded the known failures and will analyze " + jobs.length + " failed jobs");
        jobs.forEach(function(job) {
          //TODO: figure out a better solution for notifying "done"
          if (job == jobs[jobs.length -1])
              completed = true;

          let jobid = job.attributes.getNamedItem('data-job-id').nodeValue;
          let title = job.attributes.getNamedItem('title').nodeValue;
          if (jobid == '' || title == '')
            return;

          // Get repo
          var currentURL = new URL(window.location.href)
          var repo = currentURL.searchParams.get('repo')
          repo = splitRepo(window.location.href)

          url = 'https://treeherder.mozilla.org/api/project/' + repo;
          url += '/jobs/' + jobid + '/bug_suggestions/';
          fetch(url)
            .then(function(response) {
                response.json().then(function(failJson) {
                  let job_matched = false;
                  failJson.forEach(function(failure) {
                    // TODO: find failures that have test names
                    let parts = failure.search.split('|');
                    if (parts.length == 3) {
                      testname = cleanTest(parts[1].trim());

                      if (testname == 'leakcheck' && parts[2].trim() == 'tab missing output line for total leaks!')
                        return
                      if (testname == 'leakcheck' && parts[2].trim() == 'plugin missing output line for total leaks!')
                        return
                      if (testname == 'Main app process exited normally')
                        return
                    }
                    else if (!job_matched) {
                      // ignore these, usually chain reaction messages or unrelated
                      let found = false;
                      infraLines.forEach(function (line) {
                          if (failure.search.indexOf(line) != -1) {
                              found = true
                          }
                      });

                      // for infra issues or other failures, this helps
                      repeated = repeatSuccess(job);
                      if (!found && repeated < 0.5) return;

                      testname = failure.search.trim();
                    }

                    // parse title (plaform,config) and testname and match with knownFailures
                    let platconf = parseJobname(title);
                    let platform = platconf[0];
                    let config = platconf[1];
                    let pct = 0;

                    //TODO: figure out a solution for timeouts/hang on start
                    if (infraLines.indexOf(testname) != -1) {
                        //if only error (no other lines matched yet), treat as infra
                        if (!job_matched) {
                            pct = 50;
                            infra.push([platform, config, testname, jobid, 50]);
                            //analyze, if >2 leaks on same platform, then leave orange
                            let bad_infra = analyzeGreyZone(infra);
                            toggleJobs(bad_infra, classified_toggled, oranges_toggled);
                            if (bad_infra.indexOf(jobid) == -1)
                                pct = 50;
                        }
                    }
                    //TODO: figure out a solution for leaks, they happen A LOT
                    else if (testname == 'leakcheck' || testname == 'LeakSanitizer') {
                        leaks.push([platform, config, testname, jobid, 50]);
                        //analyze, if >2 leaks on same platform, then leave orange
                        let bad_leaks = analyzeGreyZone(leaks);
                        toggleJobs(bad_leaks, classified_toggled, oranges_toggled);
                        if (bad_leaks.indexOf(jobid) == -1)
                            pct = 50;
                    }
                    else if (typeof knownFailures[testname] !== 'undefined') {
                        pct = 50;
                        if (typeof knownFailures[testname][platform] !== 'undefined') {
                            pct = 75;
                            if (typeof knownFailures[testname][platform][config] !== 'undefined')
                                pct = 100;
                        }
                    }

                    let repeat = repeatSuccess(job) * 100;
                    if (repeat >= 50) pct = repeat;
                    
                    if (pct < 50) {
                        return
                    }
                    if (job_matched) {
                        return
                    }
                    job_matched = true;

                    //TODO: figure out a solution for retriggered failures
                    // if there is >2 data points and >=50% are green, ignore it

                    if (job.className.indexOf('btn-orange-classified') >= 0) {
                        job.className = job.className.replace(/btn-orange-classified/, "btn-green gp-classified");
                        classified_toggled.push([platform, config, testname, jobid, pct]);
                    } else if (job.className.indexOf('btn-orange') >= 0) {
                        job.className = job.className.replace(/btn-orange/, "btn-green gp-orange");
                        oranges_toggled.push([platform, config, testname, jobid, pct]);
                    } else {
                        console.log("BAD: " + title + " : " + testname + " : " + job.className);
                        missed.push(jobid);
                    }

                    // search for multiple failures across platforms/configs
                    let temp = [];
                    temp.push.apply(temp, classified_toggled);
                    temp.push.apply(temp, oranges_toggled);
                    let regressions = analyzeFrequentFailures(temp);
                    toggleJobs(regressions, classified_toggled, oranges_toggled);
                    if (regressions.indexOf(jobid) == -1)
                        pct = 50;

                    // TODO: if there is >1 test failure across platforms/config, increase pct
                    // TODO: if there are a collection of failures in the same dir or platform, increase pct
                    var status = document.getElementById('toggle_gp')
                    status.textContent = oranges_toggled.length + classified_toggled.length + " Known Intermittents (Analyzing)";                    
                  });
                })
            });
        })
    });
}
