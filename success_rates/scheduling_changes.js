/*
	This web extension can be used to determine the SETA
	success rate of a given range of pushes (those visible in
	a treeherder view).
*/

const activedataurl = `https://activedata.allizom.org/query`
const hgmourl = `https://hg.mozilla.org/`

const branchToHgBranch = {
	'mozilla-inbound': 'integration/mozilla-inbound/',
	'autoland': 'integration/autoland/'
}

function splitRepo(href) {
	var urls = href;
	var myurls = urls.split("?repo=");
	var mylasturls = myurls[1];
	var mynexturls = mylasturls.split("&");
	var url = mynexturls[0];
	return url
};

function timeConverter(UNIX_timestamp){
	var a = new Date(UNIX_timestamp * 1000);
	var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
	var year = a.getFullYear();
	var month = months[a.getMonth()];
	var date = a.getDate();
	var hour = a.getHours();
	var min = a.getMinutes();
	var sec = a.getSeconds();
	var time = date + ' ' + month + ' ' + year + ' ' + hour + ':' + min + ':' + sec ;
	return time;
}

function isEmptyObject(obj) {
  for (var key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      return false;
    }
  }
  return true;
}

function cleanTest(testname) {
    // TODO: split out remote and file paths, specifically in reftest
    if (testname.indexOf(' == ') != -1) {
        var left = testname.split(' == ')[0]
        var right = testname.split(' == ')[1]
        if (left.indexOf('tests/layout/') != -1)
            left = 'layout' + left.split('tests/layout')[1]
        if (right.indexOf('tests/layout/') != -1)
            right = 'layout' + right.split('tests/layout')[1]
        return left + " == " + right;
    }

    // http://localhost:50462/1545303666006/4/41276-1.html
    if (testname.indexOf('http://localhost:') == 0) {
        var parts = testname.split('/');
        return parts[parts.length-1];
    }

    return testname
}

// Used to hide and show buttons (and start processing if needed)
var calculate_coverage = true;
var calculate_seta = true;
var orig_display_settings = 'block'

function calculateSeta() {
	calculate_seta = !calculate_seta
	console.log(calculate_seta)
	var inserted_elements_seta = document.getElementById("setasuccessrateentry");
	if ((!calculate_seta) && inserted_elements_seta) {
		console.log("inside")
		inserted_elements_seta.style.display = 'none'
	} else if (calculate_seta && inserted_elements_seta) {
		inserted_elements_seta.style.display = orig_display_settings
		if (inserted_elements_seta.textContent.includes("Calculating")) {
			completeCalculation()
		}
	}
};

function calculateCoverage() {
	calculate_coverage = !calculate_coverage
	var inserted_elements_cov = document.getElementById("coveragesuccessrateentry");
	if ((!calculate_coverage) && inserted_elements_cov) {
		inserted_elements_cov.style.display = 'none'
	} else if (calculate_coverage && inserted_elements_cov) {
		inserted_elements_cov.style.display = orig_display_settings
		if (inserted_elements_cov.textContent.includes("Calculating")) {
			completeCalculation()
		}
	}
};

/* Get success rate for visible pushes */

// Get repo
var currentURL = new URL(window.location.href)
var repo = currentURL.searchParams.get('repo')
repo = splitRepo(window.location.href)

// Get first and last revision
//
// Revision entries are dynamically added to treeherder
// page so we have to check until they exist, then proceed with
// processing.
var navbarElement = document.getElementById("th-global-navbar-top");
var revnodes = document.querySelectorAll('span .revision-list');
var spanElement = null;
var currentrevnodes = 0;

var checkExist = setInterval(function() {
	revnodes = document.querySelectorAll('span .revision-list')
	if (revnodes.length >= 1 && navbarElement) {
		console.log("Exists!");
		console.log(revnodes)
		clearInterval(checkExist);

		// Insert scheduling rate dropdown
		// TODO: List options.
		currentrevnodes = revnodes.length
		var inserted_elements_cov = document.getElementById("coveragesuccessrateentry");
		var inserted_elements_seta = document.getElementById("setasuccessrateentry");
		if (!inserted_elements_cov && !inserted_elements_seta) {
			// Set up the elements
			spanElement = navbarElement.querySelector(".navbar-right");
			spanElement.insertAdjacentHTML("afterbegin",
				`
				<span class='dropdown' style='color:white'>
					<button id='setasuccessrateentry' type='button' title='Scheduling Success Rates'
					 class='btn btn-view-nav nav-menu-btn'>
					0 % SETA (Calculating)
					</button>
				<span>
				<span class='dropdown' style='color:white'>
					<button id='coveragesuccessrateentry' type='button' title='Scheduling Success Rates'
					 class='btn btn-view-nav nav-menu-btn'>
					0 % CCOV (Calculating)
					</button>
				<span>
				<span class='dropdown'>
					<button id='successrates' type='button' title='Scheduling Success Rates'
					 data-toggle='dropdown' class='btn btn-view-nav nav-menu-btn dropdown-toggle'>
					Scheduling
					</button>
					<ul id="success-dropdown" class="dropdown-menu nav-dropdown-menu-right container" role="menu" aria-labelledby="infraLabel">
						<button id='setabutton'>SETA Success</button>
						<button id='covbutton'>Coverage Success</button>
					</ul>
				</span>`
			);

			// Save original display settings
			inserted_elements_cov = document.getElementById("coveragesuccessrateentry");
			inserted_elements_seta = document.getElementById("setasuccessrateentry");
			orig_display_settings = inserted_elements_seta.style.display

			// Add onclick functions for success rate initiating
			button_cov = document.getElementById("covbutton");
			button_cov.addEventListener('click', function() {
				calculateCoverage()
			});
			button_seta = document.getElementById("setabutton");
			button_seta.addEventListener('click', function() {
				calculateSeta()
			});

			// Perform calculations requested
			inserted_elements_seta.style.display = 'none'
			inserted_elements_cov.style.display = 'none'

			completeCalculation()
		}
	} else {
		console.log("Not found...")
	}
}, 100)

var checkForNewRevs = setInterval(function() {
	var inserted_element_cov = document.getElementById("coveragesuccessrateentry");
	var inserted_element_seta = document.getElementById("setasuccessrateentry");
	if (inserted_element_cov || inserted_element_seta) {
		revnodes = document.querySelectorAll('span .revision-list')
		if (revnodes.length != currentrevnodes) {
			currentrevnodes = revnodes.length

			if (calculate_seta) {
				inserted_element_seta.textContent = "0 % SETA (Calculating)"
			}
			if (calculate_coverage) {
				inserted_element_cov.textContent = "0 % CCOV (Calculating)"
			}

			completeCalculation()
		}
	}
}, 1000)

async function completeCalculation() {
	var revnodes = document.querySelectorAll('span .revision-list')

	// Query hg.mozilla.org for dates of these revisions
	var to_date_cset = revnodes[0].querySelector('.revision-holder').textContent.trim()
	var from_date_cset = revnodes[revnodes.length-1].querySelector('.revision-holder').textContent.trim()

	var repoEntry = repo
	if (repo in branchToHgBranch) {
		repoEntry = branchToHgBranch[repo]
	}

	var url = hgmourl + repoEntry + "/json-rev/" + from_date_cset
	var from_date_cset_info = await fetch(url)
	.then(res => res.json())
	.then((out) => {
		console.log('Checkout this JSON! ', out);
	    return out;
	})
	.catch(err => { throw err });

	var url = hgmourl + repoEntry + "/json-rev/" + to_date_cset
	var to_date_cset_info = await fetch(url)
	.then(res => res.json())
	.then((out) => {
		console.log('Checkout this JSON! ', out);
	    return out;
	})
	.catch(err => { throw err });

	var from_date = timeConverter(from_date_cset_info['pushdate'][0])
	var to_date = timeConverter(to_date_cset_info['pushdate'][0])

	console.log("From date: ", from_date)
	console.log("To date: ", to_date)

	// Query active data for success rate data to process
	var otherparams = {
		headers: {
			"content-type": "application/json"
		},
		body: JSON.stringify(fixed_by_commit_query),
		method: "POST"
	}

	var fixed_by_commit_query = {
		"from":"treeherder",
		"select":[
			"job.id",
			"build.date",
			"job.type.name",
			"action.request_time",
			"build.revision12",
			"failure.notes.text"
		],
		"where":{"and":[
			{"regexp":{"repo.branch.name":".*" + repo + ".*"}},
			{"lte":{"repo.push.date":{"date":to_date}}},
			{"gte":{"repo.push.date":{"date":from_date}}},
			{"eq":{"failure.classification":"fixed by commit"}}
		]},
		"limit":50000
	}
	console.log(JSON.stringify(fixed_by_commit_query))

	var otherparams = {
		headers: {
			"content-type": "application/json"
		},
		body: JSON.stringify(fixed_by_commit_query),
		method: "POST"
	}

	// Get the response and process it
	console.log("Waiting for response...")
	fetch(activedataurl, otherparams)
	.then(data=>{return data.json()})
	.then(response=>{
		console.log(JSON.stringify(response['data']));
		if (calculate_seta) {
			getSetaSuccessRate(response['data'])
		}
		if (calculate_coverage) {
			getCoverageSuccessRate(response['data'])
		}
	}).catch(error => console.error('Error:', error));
}

function getCoverageSuccessRate(data) {
	var successElement = document.getElementById('coveragesuccessrateentry')
	successElement.style.display = orig_display_settings

	if (isEmptyObject(data)) {
		successElement.textContent = 'No data found'
		return
	}	
	successElement.textContent = 'Data found'

	var repoEntry = repo
	if (repo in branchToHgBranch) {
		repoEntry = branchToHgBranch[repo]
	}

	// For each fixed_by_commit entry, find the tests that failed in
	// the original commit with Treeherder API queries (bug_suggestions)

	// Entry Information:
	// 	build.revision12 is the revision of the failed task
	// 	job.id is the ID of the failed task
	// 	failure.notes.text contains the revision which fixed the failure
	taskrevs = data['build.revision12']
	jobids = data['job.id']
	fbcrevs = data['failure.notes.text']

	if (taskrevs.length != jobids.length ||
		jobids.length != fbcrevs.length) {
		console.log(
			"Error: Data columns do not have the same length.",
			taskrevs.length, jobids.length, fbcrevs.length
		)
		successElement.textContent = 'Data corrupted'
	}

	// Steps for each entry:
	// 1. Get bug suggestions and compile all tests found
	// 2. Clean test names to 'dir/file.' format. (Using . signifies a file extension is upcoming)
	// 3. Get HGMO file-modified information on 'failure.notes.text' revision.
	// 	(3i).  Check if files modified contains test changes - success if true.
	//  (3ii). If it only contains unrelated files => failed scheduling.
	// 4. Query activedata for coverage information on the test.
	// 5. Check if any of the modified files are in the resultant coverage.
	// 6. Success if (4) is true, else failed.

	var counter = -1
	var url = null
	var passed = 0
	var failed = 0
	var total = 0

	console.log("Iterating over FBC entries...")
	fbcrevs.forEach(async function(element, index) {
		// Get FBC revision and clean it
		counter = counter + 1
		console.log("here")
		if (counter > fbcrevs.length) {
			return true
		}
		if (element == "None" || !element) {
			return false
		}

		if (Array.isArray(element)) {
			tmp = null
			iter = 0
			while (!tmp && iter < element.length-1) {
				tmp = element[iter]
				iter = iter + 1
			}
			if (!tmp) {
				return false
			}
			element = tmp
		}

		fbcrev = element.substring(0, 12)
		taskrev = taskrevs[counter]
		jobid = jobids[counter]

		var coverage_query = {
			"from":"coverage",
			"limit":50000,
			"select":[{"name":"source","value":"source.file.name"},"test.name"],
			"where":{"and":[
				{"in":{"repo.branch.name":["try", "mozilla-central"]}},
				{"or":[
					//{"regexp":{"test.name":".*dom/media.*"}},
					//{"regexp":{"test.name":".*browser/.*"}}
				]},
				{"exists":"test.name"}
			]}
		}

		// Get bug suggestion test names
		console.log("On task revision: ", taskrev)
		url = 'https://treeherder.mozilla.org/api/project/' + repo + '/jobs/' + jobid + '/bug_suggestions/'
		fetch(url)
		.then(response => {return response.json()})
		.then(async function(data) {
			// Iterate through bug suggestions data to get test names
			var testnames = []
			data.some(function(test) {
			    let parts = test.search.split('|');
                if (parts.length == 3) {
                  testname = cleanTest(parts[1].trim());
                  if (testname == 'leakcheck')
                    return true
                  if (testname == 'Main app process exited normally')
                    return true
                } else {
                  // ignore these, usually chain reaction messages or unrelated
                  return true
				}
				testnames.push(testname)
			});

			// Increase total here
			total++

			// Remove duplicate test names and get formatted 'dir/file.' name
			testnames = new Set(testnames)
			var splittestnames = []
			testnames.forEach(function(testname) {
				splittestnames.push(
					testname.split('/').slice(-2).join('/').split('.')[0]
				)
			});

			// Get files modified
			var url = hgmourl + repoEntry + "/json-info/" + fbcrev
			var files_modified_info = await fetch(url)
			.then(res => res.json())
			.then((out) => {
				console.log('Checkout this JSON! ', out);
			    return out;
			})
			.catch(err => { throw err });

			var files_modified = files_modified_info[fbcrev]['files']
			// Check if files modified contain changes that
			// can be caught with coverage
			test_files = []
			coverage_files = []
			unrelated_files = []
			files_modified.forEach(function(file) {
				if (file.includes('testing/') ||
					file.includes('/test/') ||
					file.includes('/tests/')) {
					test_files.push(file)
				} else if ((file.includes('.js') && !file.endsWith('.json')) ||
					file.includes('.c') ||
					file.includes('.h') ||
					file.endsWith('.cpp')) {
					coverage_files.push(file)
				} else {
					unrelated_files.push(file)
				}
			});

			if (test_files.length == files_modified.length) {
				passed++
				return
			} else if (unrelated_files == files_modified.length) {
				failed++
				console.log("failed on tests (unrelated modifications): ", testnames, splittestnames)
				return
			}

			// Get coverage for all tests
			or_entry = []
			splittestnames.forEach(function(testname) {
				or_entry.push(
					{"regexp": {"test.name": ".*" + testname + "\\\\..*"}}
				)
			});

			coverage_query['where']['and'][1] = or_entry
			var otherparams = {
				headers: {
					"content-type": "application/json"
				},
				body: JSON.stringify(coverage_query),
				method: "POST"
			}

			fetch(activedataurl, otherparams)
			.then(res=>{return res.json()})
			.then(function(res) {
				if (isEmptyObject(res['data'])) {
					// No coverage data found - failed
					failed++
					console.log("failed on tests (no coverage): ", testnames, splittestnames)
					return
				}

				var coverage_data = res['data']
				var sources = coverage_data['source']
				var tests = coverage_data['test.name']

				// Now answer, can we schedule at least one of the failing tests
				// with code coverage? All we need to do now is find one
				// file in the source-files returned that is also in the files
				// modified.
				var found_file = false
				sources.some(function(source, i) {
					if (coverage_files.includes(source)) {
						found_file = true
					}
				})

				if (found_file) {
					passed++
				} else {
					failed++
					console.log("failed on tests (no coverage link): ", testnames, splittestnames)
				}

			})
			.then(function() {
				// Display success rate
				console.log("Rate: ", passed, failed, total)
				rate = 100 * passed/total
				successElement.textContent = rate.toFixed(2) + "% CCOV"
			})
			.catch(error => console.error('Error:', error));
		})
		.catch(error => console.error('Error:', error));
	});
};

function getSetaSuccessRate(data) {
	var successElement = document.getElementById('setasuccessrateentry')
	successElement.style.display = orig_display_settings

	if (isEmptyObject(data)) {
		successElement.textContent = 'No data found'
		return
	}	
	successElement.textContent = 'Data found'

	var builddate = data['build.date']
	var jobname = data['job.type.name']
	var jobdate = data['action.request_time']
	var buildrev = data['build.revision12']
	var fixedrev = data['failure.notes.text']

	var fbc = {}
	if (builddate.length != jobname.length ||
		jobname.length != jobdate.length ||
		jobdate.length != buildrev.length ||
		buildrev.length != fixedrev.length) {
		console.log(
			"Error: Data columns do not have the same length.",
			builddate.length, jobname.length, jobdate.length, buildrev.length, fixedrev.length
		)
		successElement.textContent = 'Data corrupted'
	}

	var counter = -1
	fixedrev.some(function (element, index) {
		counter = counter + 1
		if (counter > fixedrev.length) {
			return true
		}
		if (element == "None" || !element) {
			return false
		}

		if (Array.isArray(element)) {
			tmp = null
			iter = 0
			while (!tmp && iter < element.length-1) {
				tmp = element[iter]
				iter = iter + 1
			}
			if (!tmp) {
				return false
			}
			element = tmp
		}

		element = element.substring(0, 12)
		if (!(element in fbc)) {
			fbc[element] = {}
		}

		if (!(buildrev[counter] in fbc[element])) {
			fbc[element][buildrev[counter]] = false
		}

		if (jobdate[counter] - builddate[counter] < 300) {
			fbc[element][buildrev[counter]] = true
		}
	})

	var results = []
	var passed = 0
	var failed = 0
	for (const [key, value] of Object.entries(fbc)) {
		var passfail = true
		for (const [key2, value2] of Object.entries(value)) {
			if (!value2) {
				passfail = false
			}
		}
		
		if (passfail) {
			passed++
		} else {
			failed++
		}
	}

	var total = passed + failed
	var success_rate = 100 * passed/total

	successElement.textContent = success_rate.toFixed(2) + "% Seta"

	return
};
