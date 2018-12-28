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

function getSetaSuccessRate(data) {
	var successElement = document.getElementById('successrateentry')
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

	successElement.textContent = success_rate.toFixed(2) + "%"

	return
};

window.onload = async function() {
	console.log('loaded');
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
		var inserted_elements = document.getElementById("successrateentry");
		if (!inserted_elements) {
			spanElement = navbarElement.querySelector(".navbar-right");

			spanElement.insertAdjacentHTML("afterbegin",
				`
				<span class='dropdown' style='color:white'>
					<button id='successrateentry' type='button' title='Scheduling Success Rates'
					 class='btn btn-view-nav nav-menu-btn'>
					0 % (Calculating)
					</button>
				<span>
				<span class='dropdown'>
					<button id='successrates' type='button' title='Scheduling Success Rates'
					 data-toggle='dropdown' class='btn btn-view-nav nav-menu-btn dropdown-toggle'>
					Scheduling
					</button>
					<ul id="success-dropdown" class="dropdown-menu nav-dropdown-menu-right container" role="menu" aria-labelledby="infraLabel">
						<li>SETA Success</li>
						<li>Coverage Success</li>
					</ul>
				</span>`
			);

			// Calculate success rate for SETA and display
			completeSetaCalculation(revnodes)
		}
	} else {
		console.log("Not found...")
	}
}, 100)

var checkForNewRevs = setInterval(function() {
	var inserted_element = document.getElementById("successrateentry");
	if (inserted_element) {
		revnodes = document.querySelectorAll('span .revision-list')
		if (revnodes.length != currentrevnodes) {
			currentrevnodes = revnodes.length
			inserted_element.textContent = "0 % (Calculating)"
			completeSetaCalculation(revnodes)
		}
	}
}, 1000)

async function completeSetaCalculation(revnodes) {
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
	.then(response=>{console.log(JSON.stringify(response['data'])); getSetaSuccessRate(response['data'])})
	.catch(error => console.error('Error:', error));
}
