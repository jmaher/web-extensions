import datetime
import json
import os
import time
from thclient import TreeherderClient
import cProfile, StringIO, pstats


PLATFORMS = ['android-em-4-3-armv7-api16',
             'linux32', 'linux64-qr', 'linux64',
             'osx-10-10', 'macosx64-qr', 'macosx64',
             'windows7-32', 'windows10-64-qr', 'windows10-64']

FAILURES = {}

mixed = ['browser/components/search/test/browser/browser_google_behavior.js', '/webvr/webvr-enabled-by-feature-policy-attribute-redirect-on-load.https.sub.html', 'dom/vr/test/reftest/draw_rect.html == dom/vr/test/reftest/wrapper.html?draw_rect.png', '/webvr/webvr-enabled-by-feature-policy-attribute.https.sub.html', 'dom/vr/test/reftest/change_size.html', '/webvr/webvr-enabled-by-feature-policy.https.sub.html', 'dom/tests/mochitest/dom-level0/test_innerWidthHeight_script.html', 'org.mozilla.geckoview.test.NavigationDelegateTest.desktopMode', 'browser/base/content/test/static/browser_all_files_referenced.js', 'dom/serviceworkers/test/browser_storage_recovery.js', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_addons_remote_runtime.js', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_addons_temporary_addon_buttons.js', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_debug-target-pane_collapsibilities_interaction.js', 'layout/generic/test/test_plugin_focus.html', 'dom/serviceworkers/test/test_onmessageerror.html', 'testing/marionette/harness/marionette_harness/tests/unit/test_reftest.py TestReftest.test_cache_multiple_sizes', 'testing/marionette/harness/marionette_harness/tests/unit/test_reftest.py TestReftest.test_url_comparison', 'devtools/client/debugger/new/test/mochitest/browser_dbg-chrome-create.js', 'testing/firefox-ui/tests/functional/sessionstore/test_restore_windows_after_restart_and_quit.py TestSessionStoreDisabled.test_no_restore_with_quit', 'testing/firefox-ui/tests/functional/sessionstore/test_restore_windows_after_restart_and_quit.py TestSessionStoreDisabled.test_restore_with_restart', 'testing/firefox-ui/tests/functional/sessionstore/test_restore_windows_after_restart_and_quit.py TestSessionStoreEnabledAllWindows.test_with_variety', 'devtools/client/inspector/rules/test/browser_rules_shapes-toggle_02.js', 'browser/components/extensions/test/browser/browser_ext_contextMenus.js', 'browser/base/content/test/static/browser_parsable_css.js', 'toolkit/components/telemetry/tests/unit/test_TelemetrySession.js', 'browser/components/urlbar/tests/browser/browser_UrlbarInput_unit.js', 'devtools/client/inspector/extensions/test/browser_inspector_extension_sidebar.js', 'browser/components/extensions/test/browser/browser_ext_devtools_panels_elements_sidebar.js', 'browser/components/extensions/test/browser/test-oop-extensions/browser_ext_devtools_panels_elements_sidebar.js', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_addons_warnings.js', 'browser/components/extensions/test/browser/browser_ext_slow_script.js', 'browser/components/uitour/test/browser_UITour_availableTargets.js', 'browser/components/preferences/in-content/tests/browser_cookies_exceptions.js', 'browser/base/content/test/tabs/browser_multiselect_tabs_reopen_in_container.js', 'browser/base/content/test/permissions/browser_permissions.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_context_menu_store_as_global.js', 'browser/components/urlbar/tests/browser/browser_page_action_menu_share_win.js', 'browser/components/urlbar/tests/browser/browser_urlbarPlaceholder.js', 'browser/components/urlbar/tests/legacy/browser_tabMatchesInAwesomebar_perwindowpb.js', 'browser/components/urlbar/tests/legacy/browser_urlbarAddonIframe.js', 'browser/components/urlbar/tests/legacy/browser_urlbarOneOffs.js', 'browser/base/content/test/referrer/browser_referrer_middle_click_in_container.js', 'data:text/html,', 'org.mozilla.geckoview.test.GeckoSessionTestRuleTest.waitUntilCalled_throwOnNullDelegateInterface', 'org.mozilla.geckoview.test.AccessibilityTest.testMoveByCharacter', 'org.mozilla.geckoview.test.DisplayTest.doubleAcquire', 'org.mozilla.geckoview.test.FinderTest.find_matchCase', 'browser/components/preferences/in-content/tests/browser_search_subdialogs_within_preferences_6.js', 'browser/base/content/test/tabcrashed/browser_clearEmail.js', 'browser/base/content/test/tabcrashed/browser_showForm.js', 'browser/base/content/test/general/browser_restore_isAppTab.js', 'toolkit/content/tests/browser/browser_content_url_annotation.js', 'browser/base/content/test/general/browser_storagePressure_notification.js', '/html/semantics/interactive-elements/the-dialog-element/centering.html', '/html/semantics/interactive-elements/the-dialog-element/dialog-showModal.html', 'browser/components/extensions/test/browser/test-oop-extensions/browser_ext_sessions_incognito.js', 'accessible/tests/browser/e10s/browser_treeupdate_cssoverflow.js', 'toolkit/mozapps/update/tests/browser/browser_aboutDialog_bc_downloaded_staged.js', 'dom/tests/mochitest/general/test_interfaces_secureContext.html', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_addons_debug_popup.js', 'toolkit/components/antitracking/test/browser/browser_storageAccessPromiseRejectHandlerUserInteraction.js', 'layout/reftests/svg/filters/feDropShadow-01.svg == layout/reftests/svg/filters/feDropShadow-01-ref.svg', 'layout/reftests/svg/text/textLength.svg == layout/reftests/svg/text/textLength-ref.svg', 'devtools/client/framework/test/browser_target_server_compartment.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_visibility_messages.js', 'devtools/client/webconsole/test/mochitest/browser_jsterm_history.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_split_persist.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_warn_about_replaced_api.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_view_source.js', 'xpcshell-remote.ini:browser/components/extensions/test/xpcshell/test_ext_bookmarks.js', 'dom/animation/test/mozilla/test_pending_animation_tracker.html', 'dom/media/tests/mochitest/test_peerConnection_basicH264Video.html', 'browser/extensions/formautofill/test/unit/heuristics/test_de_fields.js', 'dom/indexedDB/test/browser_private_idb.js', 'toolkit/modules/tests/browser/browser_BrowserUtils.js', 'toolkit/components/thumbnails/test/browser_thumbnails_privacy.js', 'toolkit/components/telemetry/tests/browser/browser_HybridContentTelemetry.js', 'toolkit/components/passwordmgr/test/browser/browser_private_window.js', 'browser/components/customizableui/test/browser_884402_customize_from_overflow.js', 'browser/components/extensions/test/browser/test-oop-extensions/browser_ext_browsingData_pluginData.js', 'xpcshell-remote.ini:browser/components/extensions/test/xpcshell/test_ext_geckoProfiler_control.js', 'tps', 'glvideo', 'basic_compositor_video', 'ts_paint_webext', 'js/xpconnect/tests/mochitest/test_bug862380.html', '/html/browsers/origin/cross-origin-objects/cross-origin-objects.html', 'None', 'layout/mathml/tests/test_disabled_chrome.html', 'dom/bindings/test/test_sequence_wrapping.html', 'dom/base/test/test_bug116083.html', 'browser/components/newtab/test/browser/browser_discovery_styles.js', 'toolkit/components/prompts/test/test_bug619644.html', 'toolkit/content/tests/mochitest/test_bug1407085.html', 'layout/tables/test/test_bug541668_table_event_delivery.html', 'modules/libjar/test/mochitest/test_bug1173171.html', 'dom/media/webspeech/synth/test/startup/test_voiceschanged.html', 'toolkit/components/perf/test_pm.xul', 'dom/workers/test/test_worker_interfaces_secureContext.html', 'devtools/client/inspector/test/browser_inspector_highlighter-eyedropper-xul.js', '/html/infrastructure/common-dom-interfaces/collections/domstringlist.html', 'dom/file/ipc/tests/browser_ipcBlob_temporary.js', '/js/builtins/Promise-subclassing.html', 'dom/workers/test/test_navigator_secureContext.html', '/css/vendor-imports/mozilla/mozilla-central-reftests/images3/object-fit-contain-png-001e.html', 'dom/media/tests/mochitest/test_peerConnection_removeThenAddAudioTrackNoBundle.html', '/css/css-pseudo/first-letter-property-whitelist.html', '/css/CSS2/css1/c5502-imrgn-r-003.xht', '/css/CSS2/css1/c5504-imrgn-l-003.xht', '/css/CSS2/css1/c5509-ipadn-l-003.xht', '/css/CSS2/normal-flow/max-height-applies-to-012.xht', '/css/CSS2/normal-flow/max-width-applies-to-012.xht', '/css/CSS2/box-display/block-in-inline-001.xht', '/css/CSS2/box-display/block-in-inline-002.xht', '/css/CSS2/box-display/box-generation-001.xht', '/css/CSS2/box-display/box-generation-002.xht', '/css/CSS2/box-display/display-008.xht', 'dom/media/test/crashtests/1494073.html', 'toolkit/components/extensions/test/mochitest/test-oop-extensions/test_ext_contentscript_devtools_metadata.html', 'browser/base/content/test/forms/browser_selectpopup.js', 'toolkit/components/remotebrowserutils/tests/browser/browser_httpCrossOriginOpenerPolicy.js', 'xpcshell-remote.ini:toolkit/components/extensions/test/xpcshell/test_ext_permissions_uninstall.js', 'dom/canvas/test/crossorigin/test_video_crossorigin.html', '/2dcontext/drawing-paths-to-the-canvas/canvas_complexshapes_ispointInpath_001.htm', '/2dcontext/drawing-rectangles-to-the-canvas/2d.clearRect.basic.html', '/2dcontext/the-canvas-state/2d.state.saverestore.bitmap.html', '/2dcontext/drawing-text-to-the-canvas/2d.text.draw.align.center.html', '/2dcontext/drawing-images-to-the-canvas/drawimage_canvas_self.html', 'dom/media/mediasource/test/test_AVC3_mp4.html', 'org.mozilla.geckoview.test.RuntimeSettingsTest.automaticFontSize', 'browser/components/preferences/in-content/tests/siteData/browser_siteData_multi_select.js', 'browser/components/extensions/test/browser/browser_ext_windows_create_tabId.js', 'browser/components/extensions/test/browser/browser_ext_url_overrides_newtab.js', '/2dcontext/drawing-text-to-the-canvas/2d.text.draw.align.end.ltr.html', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_serviceworker_fetch_flag.js', '/2dcontext/drawing-images-to-the-canvas/2d.drawImage.9arg.basic.html', 'devtools/client/aboutdebugging-new/test/browser/browser_aboutdebugging_profiler_dialog.js', 'xpcshell-remote.ini:toolkit/components/extensions/test/xpcshell/test_ext_extension.js', 'devtools/client/application/test/browser_application_panel_debug-service-worker.js', 'dom/ipc/tests/test_blob_sliced_from_parent_process.html', 'dom/file/tests/test_nonascii_blob_url.html', 'layout/base/tests/test_frame_reconstruction_for_column_span.html', 'non262/expressions/constant-folded-labeled-statement.js', '/css/CSS2/stacking-context/opacity-change-twice-stacking-context.html', 'browser/components/preferences/in-content/tests/browser_sync_pairing.js', 'browser/components/extensions/test/browser/test-oop-extensions/browser_ext_menus_incognito.js', 'browser/components/extensions/test/browser/browser_ext_menus_incognito.js', 'browser/components/preferences/in-content/tests/siteData/browser_siteData2.js', 'devtools/client/inspector/rules/test/browser_rules_grid-toggle_01b.js', 'devtools/client/debugger/new/test/mochitest/browser_dbg-breakpoints-cond.js', 'devtools/client/debugger/new/test/mochitest/browser_dbg-breakpoints-reloading.js', 'devtools/client/inspector/rules/test/browser_rules_grid-toggle_02.js', 'devtools/client/inspector/rules/test/browser_rules_grid-toggle_04.js', 'xpcshell-remote.ini:toolkit/components/extensions/test/xpcshell/test_ext_browserSettings.js', 'devtools/client/inspector/animation/test/browser_animation_animated-property-list_unchanged-items.js', 'dom/html/test/test_bug430351.html', '/html/semantics/embedded-content/media-elements/event_timeupdate_noautoplay.html', 'browser/components/originattributes/test/browser/browser_cache.js', 'browser/base/content/test/tabs/browser_multiselect_tabs_mute_unmute.js', 'dom/media/tests/mochitest/test_peerConnection_addDataChannel.html', 'dom/media/tests/mochitest/test_peerConnection_addDataChannelNoBundle.html', 'dom/media/test/test_referer.html', 'dom/media/test/test_mediatrack_consuming_mediaresource.html', 'widget/tests/browser/browser_test_procinfo.js', 'dom/base/test/test_progress_events_for_gzip_data.html', '/service-workers/service-worker/clients-get-client-types.https.html', '/service-workers/service-worker/clients-matchall-client-types.https.html', '/service-workers/service-worker/clients-matchall-include-uncontrolled.https.html', 'netwerk/cookie/test/browser/browser_storage.js', 'netwerk/cookie/test/browser/browser_sharedWorker.js', 'browser/components/extensions/test/browser/browser_ext_runtime_setUninstallURL.js', 'toolkit/components/passwordmgr/test/mochitest/test_autocomplete_new_password.html', 'browser/components/sessionstore/test/browser_tab_label_during_restore.js', '/css/vendor-imports/mozilla/mozilla-central-reftests/text3/segment-break-transformation-removable-1.html', 'toolkit/components/passwordmgr/test/browser/browser_autocomplete_footer.js', '/bluetooth/requestDevice/canonicalizeFilter/filters-xor-acceptAllDevices.https.html', 'toolkit/components/passwordmgr/test/browser/browser_hidden_document_autofill.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_stacktrace_location_debugger_link.js', 'browser/components/extensions/test/browser/test-oop-extensions/browser_ext_settings_overrides_default_search.js', 'browser/components/extensions/test/browser/browser_ext_settings_overrides_default_search.js', 'toolkit/components/url-classifier/tests/mochitest/test_annotation_vs_TP.html', 'toolkit/components/url-classifier/tests/mochitest/test_classify_ping.html', 'dom/html/test/forms/test_valueasnumber_attribute.html', 'dom/tests/mochitest/ajax/mochikit/test_Mochikit.html', 'dom/media/webaudio/test/blink/test_iirFilterNodeGetFrequencyResponse.html', 'dom/media/webspeech/recognition/test/test_timeout.html', 'dom/media/webspeech/synth/test/test_speech_simple.html', 'dom/tests/mochitest/fetch/test_headers_sw_reroute.html', 'layout/base/tests/test_transformed_scrolling_repaints_3.html', 'dom/indexedDB/test/test_message_manager_ipc.html', 'dom/indexedDB/test/test_wasm_put_get_values.html', 'dom/ipc/tests/test_blob_sliced_from_child_process.html', 'dom/ipc/tests/test_child_docshell.html', 'layout/base/tests/test_transformed_scrolling_repaints.html', 'dom/worklet/tests/test_exception.html', 'devtools/client/webconsole/test/mochitest/browser_webconsole_time_methods.js', 'browser/base/content/test/general/browser_double_close_tab.js', 'devtools/client/webconsole/test/fixtures/stub-generators/browser_webconsole_check_stubs_console_api.js', 'org.mozilla.geckoview.test.NavigationDelegateTest.loadData_noMimeType', 'dom/base/test/chrome/test_cpows.xul', 'testing/marionette/harness/marionette_harness/tests/unit/test_click_scrolling.py TestClickScrolling.test_overflow_scroll_vertically_for_click_point_outside_of_viewport', 'testing/marionette/harness/marionette_harness/tests/unit/test_switch_frame.py TestSwitchFrame.test_should_be_able_to_carry_on_working_if_the_frame_is_deleted_from_under_us', 'toolkit/components/passwordmgr/test/mochitest/test_autofocus_js.html', 'org.mozilla.geckoview.test.AccessibilityTest.testClipboard', 'org.mozilla.geckoview.test.AccessibilityTest.testPageLoad', 'org.mozilla.geckoview.test.ContentDelegateTest.fullscreen', 'org.mozilla.geckoview.test.ContentDelegateTest.autofill_userpass', 'org.mozilla.geckoview.test.FinderTest.find_linksOnly', 'org.mozilla.geckoview.test.AccessibilityTest.testCollection', 'org.mozilla.geckoview.test.GeckoSessionTestRuleTest.waitUntilCalled_specificInterfaceMethod', 'org.mozilla.geckoview.test.GeckoSessionTestRuleTest.delegateDuringNextWait_passThroughExceptions', 'devtools/client/scratchpad/test/browser_scratchpad_recent_files.js', 'netwerk/cookie/test/browser/browser_broadcastChannel.js', 'netwerk/cookie/test/browser/browser_cookies.js', 'dom/media/test/test_eme_canvas_blocked.html', 'browser/base/content/test/keyboard/browser_toolbarKeyNav.js', 'netwerk/cookie/test/mochitest/test_document_cookie.html', 'netwerk/cookie/test/mochitest/test_fetch.html', 'netwerk/cookie/test/mochitest/test_image.html', 'netwerk/cookie/test/mochitest/test_script.html', 'dom/payments/test/test_requestShipping.html', 'browser/components/urlbar/tests/browser/browser_tabMatchesInAwesomebar.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_insecure_passwords_web_console_warning.js', 'browser/base/content/test/webrtc/browser_devices_get_user_media_unprompted_access_in_frame.js', 'toolkit/components/passwordmgr/test/browser/browser_notifications_2.js', 'dom/u2f/tests/test_multiple_keys.html', 'dom/media/test/test_cloneElementVisually_poster.html', 'toolkit/content/tests/widgets/test_videocontrols_vtt.html', 'dom/animation/test/mozilla/test_moz_prefixed_properties.html', 'layout/style/test/test_revert.html', 'devtools/client/inspector/markup/test/browser_markup_events_chrome_not_blocked.js', 'devtools/client/storage/test/browser_storage_cookies_add.js', 'devtools/client/storage/test/browser_storage_cookies_delete_all.js', '/css/css-writing-modes/text-indent-vrl-004.xht', '/webvtt/rendering/cues-with-video/processing-model/selectors/cue/font_properties.html', 'browser/components/syncedtabs/test/browser/browser_sidebar_syncedtabslist.js', '/webvtt/rendering/cues-with-video/processing-model/selectors/cue/text-shadow.html', 'toolkit/content/tests/widgets/test_videocontrols_error.html', 'dom/media/test/test_cloneElementVisually_resource_change.html', 'org.mozilla.geckoview.test.AccessibilityTest.testMutation', 'dom/media/tests/mochitest/test_peerConnection_twoVideoStreams.html', '/webdriver/tests/send_alert_text/send.py', 'browser/components/shell/test/browser_setDesktopBackgroundPreview.js', '/webrtc/RTCPeerConnection-setRemoteDescription-offer.html', 'toolkit/components/extensions/test/mochitest/test_ext_storage_manager_capabilities.html', 'toolkit/components/extensions/test/mochitest/test-oop-extensions/test_ext_storage_manager_capabilities.html', 'dom/canvas/test/webgl-conf/generated/test_conformance__glsl__bugs__angle-ambiguous-function-call.html', '/content-security-policy/worker-src/service-list.https.sub.html', 'org.mozilla.geckoview.test.PromptDelegateTest.popupTest', 'toolkit/components/url-classifier/tests/mochitest/test_bug1254766.html', 'toolkit/components/url-classifier/tests/mochitest/test_cachemiss.html', 'toolkit/components/url-classifier/tests/mochitest/test_classifier.html', 'toolkit/components/url-classifier/tests/mochitest/test_classifier_match.html', '/css/CSS2/visufx/clip-001.xht', '/webvtt/rendering/cues-with-video/processing-model/selectors/cue_function/underline_object/underline_namespace.html', 'browser/base/content/test/sanitize/browser_sanitize-formhistory.js', 'devtools/client/responsive.html/test/browser/browser_device_width.js', 'devtools/client/storage/test/browser_storage_delete_all.js', 'accessible/tests/crashtests/884202.html', 'dom/tests/mochitest/chrome/test_selectAtPoint.html', '/html/semantics/embedded-content/media-elements/track/track-element/track-cue-rendering-after-controls-removed.html', 'browser/base/content/test/static/browser_misused_characters_in_strings.js', 'toolkit/components/url-classifier/tests/mochitest/test_classify_by_default.html', 'mobile/android/tests/browser/chrome/test_settings_fontinflation.html', 'dom/presentation/tests/mochitest/test_presentation_1ua_sender_and_receiver_oop.html', 'dom/presentation/tests/mochitest/test_presentation_availability.html', '/html/editing/editing-0/spelling-and-grammar-checking/spelling-markers-009.html', '/html/editing/editing-0/spelling-and-grammar-checking/spelling-markers-010.html', 'browser/components/contextualidentity/test/browser/browser_aboutURLs.js', '/webrtc/RTCDataChannel-send.html', 'browser/components/urlbar/tests/browser/browser_action_searchengine.js', 'toolkit/components/passwordmgr/test/browser/browser_http_autofill.js', 'dom/crypto/test/browser/browser_WebCrypto_telemetry.js', '/IndexedDB/idb_binary_key_conversion.htm', 'dom/indexedDB/test/test_blocked_order.html', 'devtools/client/webconsole/test/mochitest/browser_webconsole_warning_groups.js', 'devtools/client/webconsole/test/mochitest/browser_webconsole_warning_group_content_blocking.js', 'The mochitest suite: mochitest-media ran with return status: FAILURE', 'TEST-UNEXPECTED-FAIL | gfx/layers/apz/test/mochitest/test_group_touchevents-4.html | helper_bug1509575.html | visual viewport did scroll - got 18, expected 100', 'timed out after 600 seconds of no output', '0 ERROR Automation Error: Exception caught while running tests', 'self.dismiss_alert(lambda: self.marionette.navigate(url))', 'Loading initial page http://web-platform.test:8000/testharness_runner.html failed. Ensure that the there are no other programs bound to this port and that your firewall rules or network setup does not prevent access.\\eTraceback (most recent call last):', 'The mochitest suite: chrome ran with return status: FAILURE', 'The mochitest suite: mochitest-webgl1-core ran with return status: FAILURE', 'Automation Error: Received unexpected exception while running application', 'The reftest suite: jsreftest ran with return status: FAILURE', '# TBPL WARNING #', "KeyError: 'preferences'", 'Caught exception: <urlopen error [Errno -3] Temporary failure in name resolution>', 'InvalidArgumentException: Unknown pointerType: [object String] "pen"', "Automation Error: mozprocess timed out after 1000 seconds running ['/builds/worker/workspace/build/venv/bin/python', '-u', '/builds/worker/workspace/build/tests/reftest/runreftest.py', '--total-chunks', '8', '--this-chunk', '4', '--appname=/builds/worker/workspace/build/application/firefox/firefox', '--utility-path=tests/bin', '--extra-profile-file=tests/bin/plugins', '--symbols-path=https://queue.taskcluster.net/v1/task/Hxxni36uQEGsFUZoDadr6Q/", 'FATAL ERROR: AsyncShutdown timeout in profile-change-teardown Conditions: [{"name":"Extension shutdown: screenshots@mozilla.org","state":{"state":"Shutdown: Storage"},"filename":"resource://gre/modules/addons/XPIProvider.jsm","lineNumber":2318,"stack":["resource://gre/modules/addons/XPIProvider.jsm:startup/<:2318"]}] At least one completion condition failed to complete within a reasonable amount of time. Causing a crash to ensure that we do no', 'raptor-main TEST-UNEXPECTED-FAIL: no raptor test results were found for raptor-sunspider-firefox', 'raptor-main TEST-UNEXPECTED-FAIL: no raptor test results were found for raptor-tp6m-amazon-geckoview, raptor-tp6m-facebook-geckoview, raptor-tp6m-google-geckoview, raptor-tp6m-youtube-geckoview', 'Assertion failure: mIsSome, at /builds/worker/workspace/build/src/obj-firefox/dist/include/mozilla/Maybe.h:488', 'Got 2 unexpected crashes', 'Assertion failure: mGLContext, at /builds/worker/workspace/build/src/gfx/layers/opengl/CompositorOGL.cpp:1943', "Assertion failure: mRawPtr != nullptr (You can't dereference a NULL nsCOMPtr with operator->().), at /builds/worker/workspace/build/src/obj-firefox/dist/include/nsCOMPtr.h:843"]

def loadFailures(date):
    global FAILURES

    filename = 'failures-%s.json' % date
    with open(filename, 'r') as f:
        data = json.load(f)
    FAILURES = data


def loadFBCTests(thclient, date, start=0, end=None):
    global FAILURES

    if not FAILURES:
        loadFailures(date)

    filename = cacheName('fixed_by_commit_testnames-%s.json' % date)
    if os.path.exists(filename):
        with open(filename, 'r') as fHandle:
            data = json.load(fHandle)
        FAILURES['fixed_by_commit_tests'] = data
        return

    testnames = []
    raw_data = {}
    raw_filename = cacheName('raw_fixed_by_commit_testnames.json')
    if os.path.exists(raw_filename):
        with open(raw_filename, 'r') as fHandle:
            raw_data = json.load(fHandle)

    new_failures = False
    for jobid in FAILURES['fixed_by_commit']:
        # load raw failures
        # if testname, save off and store in whitelist database
        if not os.path.exists(raw_filename) or \
           str(jobid[0]) not in raw_data.keys():
            new_failures = True
            print("missing key: %s" % jobid[0])
            try:
                failures = thclient._get_json('jobs/%s/bug_suggestions' % jobid[0],
                                              project=jobid[1])
            except:
                print("FAILURE retrieving bug_suggestions: %s" % jobid[0])
                failures = [{'search': ''}]
            raw_data[str(jobid[0])] = failures
        else:
            failures = raw_data[str(jobid[0])]

        lines = []
        for f in failures:
            if len(f['search'].split('|')) == 3:
                lines.append(f['search'].split('|')[1])

        job_tests = []
        for line in lines:
            name = cleanTest(line.strip())
            if not name or name.strip() == '':
                continue

            # ignore generic messages
            if name in ['automation.py']:
                continue

            # ignore talos tests for fixed by commit
            # TODO: make this more complete
            if name in ['damp', 'tp5n', 'tp5o', 'about_preferences_basic']:
                continue

            # we find that unique failures that exist already is all we need
            if name not in testnames and name in FAILURES.keys():
                job_tests.append(name)
                break

        testnames.extend(job_tests[start:end])

    with open(filename, 'w') as f:
        json.dump(testnames, f)
    if not os.path.exists(raw_filename) or new_failures:
        with open(raw_filename, 'w') as f:
            json.dump(raw_data, f)
    FAILURES['fixed_by_commit_tests'] = testnames


def cacheName(filename):
    return "cache/%s" % filename


def loadFailureLines(thclient, jobs, branch, revision, force=False):
    retVal = []

    filename = cacheName('%s-%s-jobs.json' % (branch, revision))
    if not force and os.path.exists(filename):
        try:
            with open(filename, 'r') as fHandle:
                data = json.load(fHandle)
            return data
        except json.decoder.JSONDecodeError:
            pass

    for job in jobs:
        # get bug_suggestions, not available via client, so doing a raw query
        try:
            failures = thclient._get_json('jobs/%s/bug_suggestions' % job['id'],
                                          project='%s' % branch)
        except:
            print("FAILURE retrieving bug_suggestions: %s" % job['id'])
            job['failure_lines'] = ['']
            retVal.append(job)
            continue

        lines = [f['search'].encode('ascii', 'ignore').decode('utf-8') for f in failures]
        job['failure_lines'] = lines
        retVal.append(job)

    with open(filename, 'w') as f:
        json.dump(retVal, f)

    return retVal


def loadAllJobs(thclient, branch, revision):
    filename = cacheName("%s-%s.json" % (branch, revision))
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    pushes = thclient.get_pushes(branch, revision=revision)
    retVal = []
    for push in pushes:
        done = False
        count = 2000
        offset = 0
        while not done:
            jobs = thclient.get_jobs(branch,
                                     push_id=push['id'],
                                     count=count,
                                     offset=offset)
            for job in jobs:
                retVal.append(cleanConfigs(job))

            if len(jobs) == count:
                offset += count
            else:
                done = True
    with open(filename, 'w') as f:
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
        if job not in retVal:
            retVal.append(job)
    return retVal


def cleanConfigs(job):
    platform = job['platform']
    config = job['platform_option']

    if config == 'pgo' or config == 'shippable':
        config = 'opt'

    if platform.startswith('macosx64'):
        platform = platform.replace('macosx64', 'osx-10-10')

    job['config'] = config.encode('ascii', 'ignore').decode('utf-8')
    job['platform'] = platform.encode('ascii', 'ignore').decode('utf-8')
    return job


def cleanTest(testname):
    try:
        testname = str(testname)
    except UnicodeEncodeError:
        return ''

    if testname.startswith('pid:'):
        return ''

    if ' == ' in testname or ' != ' in testname:
        if ' != ' in testname:
            left, right = testname.split(' != ')
        elif ' == ' in testname:
            left, right = testname.split(' == ')

        if 'tests/layout/' in left and 'tests/layout/' in right:
            left = 'layout%s' % left.split('tests/layout')[1]
            right = 'layout%s' % right.split('tests/layout')[1]
        elif 'build/tests/reftest/tests/' in left and \
             'build/tests/reftest/tests/' in right:
            left = '%s' % left.split('build/tests/reftest/tests/')[1]
            right = '%s' % right.split('build/tests/reftest/tests/')[1]
        elif testname.startswith('http://10.0'):
            left = '/tests/'.join(left.split('/tests/')[1:])
            right = '/tests/'.join(right.split('/tests/')[1:])
        testname = "%s == %s" % (left, right)

    if 'build/tests/reftest/tests/' in testname:
        testname = testname.split('build/tests/reftest/tests/')[1]

    if 'jsreftest.html' in testname:
        testname = testname.split('test=')[1]

    if testname.startswith('http://10.0'):
        testname = '/tests/'.join(testname.split('/tests/')[1:])

    # http://localhost:50462/1545303666006/4/41276-1.html
    if testname.startswith('http://localhost:'):
        parts = testname.split('/')
        testname = parts[-1]

    if " (finished)" in testname:
        testname = testname.split(" (finished)")[0]

    # TODO: does this affect anything?
    if testname in ['Main app process exited normally',
                    None,
                    'Last test finished',
                    '(SimpleTest/TestRunner.js)']:
        return ''

    testname = testname.strip()
    testname = testname.replace('\\', '/')
    return testname


# TODO: make this more optimized, this is called everytime,
#       maybe cache the results of repeated jobs?
# if there is >2 data points and >=50% are green, ignore it
def repeatSuccessJobs(failedjob, allJobs):
    matched_jobs = filterJobsByName(allJobs, failedjob['job_type_name'])
    success = len([x for x in matched_jobs if x['result'] == 'success'])
    if success + len(matched_jobs) < 2:
        return 0.5

    return (success / len(matched_jobs))


def analyzeGreyZone(list, max_failures=3):
    bad_items = []
    pmap = {}
    for item in list:
        key = item[0]  # platform
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
        key = item[2]  # testname
        if key not in pmap.keys():
            pmap[key] = []

        if item[3] not in pmap[key]:
            pmap[key].append(item[3])

        if len(pmap[key]) >= max_failures:
            bad_items.extend([x for x in pmap[key] if x not in bad_items])
    return bad_items


def analyzeSimilarJobs(list, alljobs, max_failures=3):
    # look if all jobs failed, even if we only ran a few- also match suite level
    bad_items = []
    # find the suite name, not platform, not chunk, but flavor is ok
    suites = ['talos', 'raptor', 'awsy',
              'mochitest', 'web-platform-tests', 'reftest', 'browser-screenshots',  # subsuites
              'crashtest',
              'xpcshell',
              'firefox-ui',
              'marionette',
              'source-test', 'generate-profile',
              'robocop', 'junit',
              'cppunit', 'gtest', 'jittest']

    failed_suites = []
    for item in list:
        try:
            suite = [x for x in suites if x in item[4]][0]
        except:
            print("missing suite: %s" % item[4])
            continue

        if suite in ['mochitest', 'web-platform-tests', 'reftest']:
            # subsuites
            if suite == 'reftest' and 'jsreftest' in item[4]:
                suite = 'jsreftest'
            elif suite == 'reftest' and 'gpu' in item[4]:
                suite = 'reftest'
            elif suite == 'web-platform-tests' and 'reftest' in item[4]:
                suite = 'web-platform-tests-reftests'
            elif suite == 'web-platform-tests' and 'wdspec' in item[4]:
                suite = 'web-platform-tests-wdspec'
            else:
                sub = item[4].split(suite)[1]
                parts = sub.split('-')

                if len(parts) > 1 and parts[1] not in ['e10s', 'headless', 'no']:
                    try:
                        x = int(parts[1])
                    except ValueError:
                        suite = 'mochitest-%s' % parts[1]

        if suite not in failed_suites:
            failed_suites.append(suite)

    for suite in failed_suites:
        failures = [x for x in list if suite in x[4]]
        all = [x for x in alljobs if suite in x['job_type_name']]

        # if 75% of all jobs are failed jobs, then add to bad_items
        if len(failures) / (len(all) * 1.0) >= .75:
            bad_items.extend(failures)
    return [x[3] for x in bad_items]


def analyzeSimilarFailures(list, max_failures=3):
    bad_items = []
    pmap = {}
    for item in list:
        key = item[2]  # testname
        # strip the leafname and look for directory
        parts = key.split('/')
        if len(parts) > 1:
            key = '/'.join(parts[:-1])

        if key not in pmap.keys():
            pmap[key] = []

        if item[3] not in pmap[key]:
            pmap[key].append(item[3])

        if len(pmap[key]) > max_failures:
            bad_items.extend([x for x in pmap[key] if x not in bad_items])
    return bad_items


def filterLowestCommonClassification(results):
    """
      For all testfailures identified, ensure jobs are not marked as
      intermittent if there is another reason not to by rewriting
      classification

      TODO: we should adjust confidence, need to revisit
    """

    # classification priority
    high = ['newfailure', 'previousregression', 'unknown']

    uniqueids = []
    for id in [x[3] for x in results]:
        if id not in uniqueids:
            uniqueids.append(id)

    # for each job, find all tests, identify 'high' classifications
    for id in uniqueids:
        matches = [x for x in results if x[3] == id]
        highvalue = [x[3] for x in matches if x[5] in high]
        # if no high confidence or only 1 failure, ignore
        if len(highvalue) == 0 or len(matches) == 1:
            continue

        # rewrite classification to append '-low'
        for x in results:
            if x[3] == id:
                x[5] = "%s-low" % x[5]

    return results


def analyzeJobs(jobs, alljobs, ignore, verbose=False):
    '''
        Currently sheriffs look at a task and annotate the first test failure
        99% of the time ignoring the rest of the failures.  Here we analyze
        all failures for a given task which result in more unknowns.
        As a solution we will ignore failures that:
         * are known infra or leak warnings
         * > 5 lines (only look at first 5 lines)
         * traceback, harness/mozharness messages
         * assertions

        Unlike the sheriffs we will be looking only at a single commit, not
        taking into account similar failures on previous or future commits,
        nor knowing history of intermittents.  We will have access to 14 days
        of test failures and 30 days of regressions so we have a reference set
        to use in order to provide a classification for each job.

        We will parse each line looking for a 'testname', I will ignore the
        specific failure.

        Given the testname, we will store results for a job in a tuple of:
        [platform, config, testname, jid, jobname, classification, confidence]

        Classification severity should be:
          * unknown (0) - default
          * infra (1)
          * leak (2)
          * intermittent (3)
          * crash (4)
          * newfailure (5)
          * previousregression (6)
          * regression (7)

        Confidence will be based on factors such as repeated runs, a known
        regression from the past, and frequency across platform and the entire
        push.

        As this is intended to run in real time, we will sometime categorize
        an orange as intermittent but then on future results we will find
        frequency of the failure and could mark it as a regression or unknown.

        When done analyzing a job, we will classify all failures and then
        pick the highest failure classification for the job.  The intended
        consumers of this api will be:
          * push health in treeherder (per test analysis, not per job)
          * meta analysis over time (matching results to sheriff annotations)
          * potentially altering default view of orange jobs in treeherder

        Because the consumers are a wide variety, I want to ensure we provide
        accurate information related to both per test failure and per job
        failure.
    '''

    infra = ['raptor-main TEST-UNEXPECTED-FAIL: no raptor test results were found',
             'Uncaught exception: Traceback (most recent call last):']
    ignore_leaks = ['tab missing output line for total leaks!',
                    'plugin missing output line for total leaks!',
                    'process() called before end of test suite']

    results = []
    reasons = {}
    for job in jobs:
        job_results = []

        last_testname = ''
        for line in job['failure_lines'][:5]:
            result = [job['platform'],
                      job['config'],
                      '',
                      job['id'],
                      job['job_type_name'],
                      "unknown",             # classificaiton
                      50]                    # confidence

            line = line.encode('ascii', 'ignore')
            testname = str(line.strip())
            # format: "TEST-UNEXPECTED-FAIL | <name> | <msg>"
            parts = line.split(b'|')
            if len(parts) == 3:
                testname = cleanTest(parts[1].strip())
                result[5] = 'intermittent'
                if parts[2].strip() in ignore_leaks:
                    result[5] = 'leak'
                if parts[2].strip() in ignore:
                    result[5] = 'infra'
                if testname == 'leakcheck':
                    result[5] = 'leak'
                last_testname = testname
            elif len(parts) == 2:
                result[5] = 'unknown'
                # not a formatted error
                continue
            elif last_testname != '':
                # ignore non test failure lines after a test failure line
                break

            if [x for x in ignore if len(testname.split(x)) > 1]:
                break
            if not testname or testname == '':
                continue

            result[2] = testname
            job_results.append(result)
        results.extend(job_results)
    return results


def analyzePush(client, branch, push, ignore_list, verbose=False):
    jobs = loadAllJobs(client, branch, push['revision'])

    # find failed jobs, not tier-3, not blue(retry), just testfailed
    failed_jobs = filterFailedJobs(jobs)
    failed_jobs = [j for j in failed_jobs if j['tier'] in [1, 2]]
#    failed_jobs = [j for j in failed_jobs if j['result'] == 'testfailed']

    # temporarily filter out test-verify
#    failed_jobs = [j for j in failed_jobs if len(j['job_type_name'].split('test-verify')) == 1]

    failed_jobs = loadFailureLines(client,
                                   failed_jobs,
                                   branch,
                                   push['revision'])

    # get list of fixed_by_commit jobs
    regressed_jobs = filterRegressions(jobs)
    regressed_ids = []
    for x in regressed_jobs:
        if x['id'] not in regressed_ids:
            regressed_ids.append(x['id'])
    regressed_ids = [x['id'] for x in regressed_jobs]

    v = False
    oranges = analyzeJobs(failed_jobs, jobs, ignore_list, v)
    known_fbc = []
    for orange in oranges:
        if orange[3] in regressed_ids:
            known_fbc.append(orange[2])
    return oranges, regressed_ids, len(jobs)

def getPushes(client, branch, date):
    parts = date.split('-')
    d = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]))
    start_date = time.mktime(d.timetuple())
    end_date = start_date + 86400

    filename = cacheName('pushes-%s.json' % date)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            pushes = json.load(f)
    else:
        pushes = client.get_pushes(branch,
                                   count=1000,
                                   push_timestamp__gte=start_date,
                                   push_timestamp__lte=end_date)
        with open(filename, 'w') as f:
            json.dump(pushes, f)

    return pushes


client = TreeherderClient(server_url='https://treeherder.mozilla.org')
branch = 'autoland'

dates = []
for iter in range(2, 32):
    if iter < 10:
        iter = "0%s" % iter
    dates.append('2019-01-%s' % iter)
for iter in range(1, 29):
    if iter < 10:
        iter = "0%s" % iter
    dates.append('2019-02-%s' % iter)
for iter in range(1, 32):
    if iter < 10:
        iter = "0%s" % iter
    dates.append('2019-03-%s' % iter)

#dates = ['2019-03-26', '2019-03-27', '2019-03-28']
#dates = ['2019-03-26']

ignore = ['[taskcluster:error]']
print("date, pushes, tests, other")
total_tests = 0
total_other = 0
all_tests = []
all_other = []
total_pushes = 0


#pr = cProfile.Profile()
#pr.enable()

all_fbc = []
fbc_tests = []
fbc_other = []
total_jobs = 0
raw_tests = {}
raw_testids = {}
for date in dates:
    loadFBCTests(client, date)
    for test in FAILURES['fixed_by_commit_tests']:
        if test not in all_fbc:
            all_fbc.append(test)

    pushes = getPushes(client, branch, date)

    tests = []
    other = []
    all_results = []
    for push in pushes:
        results, regressed_ids, num_jobs = analyzePush(client, branch, push, ignore_list=ignore, verbose=True)
        t = {}
        for r in results:
            if r[2] not in t.keys():
                t[r[2]] = []
            t[r[2]].append(r)

        before = len(results)
#        results = []
#        for x in t:
#            if len(t[x]) > 1:
#                results.extend(t[x])
    
        #   platform,   config,  testname,  jobid, jobname, classification, confidence
        # [u'osx-10-10', u'opt', 'Return code: 1', 219729843, u'test-macosx64/opt-mochitest-devtools-chrome-e10s-3', 'unknown', 50]
        for r in results:
            parts = r[4].split('/')
            if len(parts) == 1:
                continue
            config = parts[0] + '/' + parts[1].split('-')[0]

            if r[5] == 'intermittent':
                total_tests += 1
                if r[2] not in raw_tests.keys():
                    raw_tests[r[2]] = {}
                    raw_testids[r[2]] = {}
                if config not in raw_tests[r[2]].keys():
                    raw_tests[r[2]][config] = []
                    raw_testids[r[2]][config] = []
                raw_tests[r[2]][config].append(push['push_timestamp'])
                raw_testids[r[2]][config].append(r[3])

                if r[2] not in all_tests and r[2] not in tests:
                    if r[3] not in regressed_ids:
                        tests.append(r[2])
                    elif r[2] not in fbc_tests:
                        fbc_tests.append(r[2])
            else:
                total_other += 1
                if r[2] not in all_other and r[2] not in other:
                    if r[3] not in regressed_ids:
                        other.append(r[2])
                    elif r[2] not in fbc_other:
                        fbc_other.append(r[2])

        total_jobs += num_jobs
    print("%s, %s, %s, %s, %s" % (date, len(pushes), len(tests), len(other), num_jobs))
    all_tests.extend(tests)
    all_other.extend(other)
    total_pushes += len(pushes)

mixed_tests = [x for x in fbc_tests if x in all_tests]
mixed_other = [x for x in fbc_other if x in all_other] 
print("\n\ndate, pushes, tests, unique tests, fbc_tests, mixed_tests, other, unique other, fbc_other, mixed_other, fbc tests")
print("%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s" % (date, total_pushes, total_tests, len(all_tests), len(fbc_tests), len(mixed_tests), total_other, len(all_other), len(fbc_other), len(mixed_other), len(all_fbc), total_jobs))

print("\nintermittent tests vs random:")
intermittent = []
random = []
intermittent_jobs = []
random_jobs = []
for test in raw_tests.keys():
    for config in raw_tests[test]:
        # if config has 2 failures with a timestamp within 21 days it is intermittent
        found = False
        if len(raw_tests[test][config]) > 1:
            for iter in range(0, len(raw_tests[test][config]) -1):
                if (raw_tests[test][config][iter+1] - raw_tests[test][config][iter]) < 86400 * 14:
                    found = True
                    break

        if found:
            intermittent_jobs.extend(raw_testids[test][config])
        else:
            random_jobs.extend(raw_testids[test][config])

    if found:
        intermittent.append(test)            
    else:
        random.append(test)

print("intermittent jobs: %s" % len(intermittent_jobs))
print("random jobs: %s" % len(random_jobs))
print("intermittent tests: %s" % len(intermittent))
print("random tests: %s" % len(random))

"""
pr.disable()
s = StringIO.StringIO()
sortby = 'cumulative'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print s.getvalue()
"""