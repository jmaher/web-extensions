# web-extensions

A collection of web-extensions for Firefox.

## success_rates

This web-extension works on all treeherder pages and shows the SETA scheduling success rate given the revisions that are listed in the treeherder view. When more revisions are addded to the view, the success rate will recompute itself.

Instructions for setup: 
1. Clone this repository locally.
2. Go to `about:debugging` in Firefox.
3. Click `Load Temporary Add-on` and point it to a file in the `success_rates` folder (any file).
4. Now it's loaded so you can go to treeherder on mozilla-inbound or autoland to find success rate scores. i.e. try this [link](https://treeherder.mozilla.org/#/jobs?repo=mozilla-inbound&searchStr=decisionkjhk&fromchange=693c18f60a0fc7dcac8f5162de4f248b0570e27e).

Notes:
1. When there is no fixed-by-commit data found for a requested range, 'No data found' will be displayed at the top.
2. Sometimes there are unavoidable network errors that can be seen in the log - a refresh will usually solve these. (The active data query can take a while as well).
