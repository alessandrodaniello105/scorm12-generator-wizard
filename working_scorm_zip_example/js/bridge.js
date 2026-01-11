var XismBridge = (function () {
    "use strict";

    var XismBridge = function () {
        // "xapi" or "scorm2004" or "scorm12"
        this.courseMode = "";
        this.activity = "";
        this.agent = {};
        this.homePage = "";
        this.name = "";
        this.courseId = "";

        this.constants = {
            activityProfileIri: "http://adlnet.gov/xapi/profile/scorm/activity-profile",
            activityStateIri: "http://adlnet.gov/xapi/profile/scorm/activity-state",
            actorProfileIri: "http://adlnet.gov/xapi/profile/scorm/actor-profile",
            attemptStateIri: "http://adlnet.gov/xapi/profile/scorm/attempt-state"
        };
    };

    var getUrlParams = function () {
        var urlParams;
        var match,
            pl = /\+/g,  // Regex for replacing addition symbol with a space
            search = /([^&=]+)=?([^&]*)/g,
            decode = function (s) {
                return decodeURIComponent(s.replace(pl, " "));
            },
            query = window.location.search.substring(1);

        urlParams = {};
        while (match = search.exec(query)) {
            urlParams[decode(match[1])] = decode(match[2]);
        }

        return urlParams;
    };

    XismBridge.prototype.SetMode = function(mode) {
        this.courseMode = mode;
        if (mode === "scorm12" || mode === "scorm2004") {
            scormVersion = mode.substr(5);
            updateObjectToFind();
        }
    };

    XismBridge.prototype.StartCourse = function (id) {
        var attemptIri, api;
        if (this.courseMode === 'xapi') {
            var urlParams = getUrlParams();

            //Set activity and agent values
            this.activity = urlParams.activity_id;
            this.courseId = id;
            var actor = JSON.parse(urlParams.actor);
            var account = actor.account[0];
            this.homePage = account.accountServiceHomePage;
            this.name = account.accountName;
            this.agent = {
                account: {
                    homePage: this.homePage,
                    name: name
                }
            };

            attemptIri = this.activity + "?attemptId=" + generateUUID();
            ADL.XAPIWrapper.sendState(this.activity, this.agent, this.constants.activityStateIri, null, {attempts: [attemptIri]});

            window.localStorage[this.activity] = attemptIri;
            var statement = getBasicStatement(this.agent.account, this.activity, this.courseId);
            statement.verb = ADL.verbs.initialized;
            statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];

            ADL.XAPIWrapper.sendStatement(statement);
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            api.Initialize("");
            api.SetValue("cmi.exit", "suspend");
            api.Commit("");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            api.LMSInitialize("");
            api.LMSSetValue("cmi.core.exit", "suspend");
            api.LMSCommit("");
        }
    };

    XismBridge.prototype.EndCourse = function () {
        var api;
        if (this.courseMode === 'xapi') {
            var statement = getBasicStatement(this.agent.account, this.activity, this.courseId);
            statement.verb = ADL.verbs.terminated;
            statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];

            ADL.XAPIWrapper.sendStatement(statement);
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            api.SetValue("cmi.exit", "suspend");
            api.Commit("");
            api.Terminate("");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            api.LMSSetValue("cmi.core.exit", "suspend");
            api.LMSCommit("");
            api.LMSFinish("");
        }
    };

    XismBridge.prototype.SetScore = function (score) {
        var api;
        if (this.courseMode === 'xapi') {
            var statement = getBasicStatement(this.agent.account, this.activity, this.courseId);
            statement.verb = ADL.verbs.scored;
            statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];
            statement.result = {score: {raw: parseFloat(score)}};
            ADL.XAPIWrapper.sendStatement(statement);
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            api.SetValue("cmi.score.raw", score);
            api.Commit("");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            api.LMSSetValue("cmi.core.score.raw", score);
            api.LMSCommit("");
        }
    };

    XismBridge.prototype.GetScore = function () {
        var api;
        if (this.courseMode === 'xapi') {
            var verb = ADL.verbs.scored;
            var statements = ADL.XAPIWrapper.getStatements({"verb": verb.id});
            var singleStatement = statements.statements[0];
            return singleStatement.result.score.raw;
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            return api.GetValue("cmi.score.raw");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            return api.GetValue("cmi.core.score.raw");
        }
    };

    XismBridge.prototype.SetCompletionStatus = function (status) {
        var api;
        if (this.courseMode === 'xapi') {
            var statement = getBasicStatement(this.agent.account, this.activity, this.courseId);
            if (status === "completed") {
                statement.verb = ADL.verbs.completed;
                statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];
                ADL.XAPIWrapper.sendStatement(statement);
            }
            else {
                throw "Cannot set a completion status other than complete.";
            }
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            api.SetValue("cmi.completion_status", status);
            api.Commit("");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            api.LMSSetValue("cmi.core.lesson_status", status);
            api.LMSCommit("");
        }
    };

    XismBridge.prototype.GetCompletionStatus = function () {
        var api;
        if (this.courseMode === 'xapi') {
            var verb = ADL.verbs.completed;
            var statementsObject = ADL.XAPIWrapper.getStatements({"verb": verb.id});
            return statementsObject.statements.length > 0 ? "completed" : "incomplete";
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            return api.GetValue("cmi.completion_status");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            return api.LMSGetValue("cmi.core.lesson_status");
        }
    };

    XismBridge.prototype.SetSuccessStatus = function (status) {
        var api;
        if (this.courseMode === 'xapi') {
            var statement = getBasicStatement(this.agent.account, this.activity, this.courseId);
            if (status === "passed") {
                statement.verb = ADL.verbs.passed;
                statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];
                ADL.XAPIWrapper.sendStatement(statement);
            }
            else if (status === "failed") {
                statement.verb = ADL.verbs.failed;
                statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];
                ADL.XAPIWrapper.sendStatement(statement);
            }
            else {
                throw "Not a valid status. Valid options are passed and failed.";
            }

        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            api.SetValue("cmi.success_status", status);
            api.Commit("");
        }
        else if (this.courseMode === 'scorm12') {
            // Down-convert SCORM 2004 specific keys to 1.2.
            if (status === "unknown") {
                status = "incomplete";
            }
            api = getAPIHandle();
            api.LMSSetValue("cmi.core.lesson_status", status);
            api.LMSCommit("");
        }
    };

    XismBridge.prototype.GetSuccessStatus = function () {
        var api;
        if (this.courseMode === 'xapi') {
            var verb = ADL.verbs.passed;
            var statementsObject = ADL.XAPIWrapper.getStatements({"verb": verb.id});
            var mostRecent = statementsObject.statements[0];
            verb = ADL.verbs.failed;
            statementsObject = ADL.XAPIWrapper.getStatements({"verb": verb.id, "since": mostRecent.stored});
            return statementsObject.statements.length > 0 ? "failed" : "passed";
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            return api.GetValue("cmi.success_status");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            return api.LMSGetValue("cmi.core.lesson_status");
        }
    };

    XismBridge.prototype.SetBookmark = function (location) {
        var api;
        if (this.courseMode === 'xapi') {
            ADL.XAPIWrapper.sendState(this.activity, this.agent, this.constants.activityStateIri, null, {bookmark: [location]});
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            api.SetValue("cmi.location", location);
            api.Commit("");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            api.LMSSetValue("cmi.core.lesson_location", location);
            api.LMSCommit("");
        }
    };

    XismBridge.prototype.GetBookmark = function () {
        var api;
        if (this.courseMode === 'xapi') {
            var location = ADL.XAPIWrapper.getState(this.activity, this.agent, this.constants.activityStateIri);
            return location.bookmark[0];
        }
        else if (this.courseMode === 'scorm2004') {
            api = getAPIHandle();
            return api.GetValue("cmi.location");
        }
        else if (this.courseMode === 'scorm12') {
            api = getAPIHandle();
            return api.LMSGetValue("cmi.core.lesson_location");
        }
    };




    // TODO: Fix SCORM 1.2 behavior below here.
    // TODO: FIX SCORM 1.2 NOW




    XismBridge.prototype.SetInteractionObject = function (obj) {
        var i, item;
        if (this.courseMode === 'xapi') {
            var statement = getBasicStatement(this.agent.account, this.activity, this.courseId);
            statement.verb = ADL.verbs.interacted;

            statement.object = {
                "id": obj.id,
                "definition": {
                    "interactionType": obj.type,
                    "description": {"en": obj.description},
                    "correctResponsesPattern": obj.correct_responses
                }
            }

            statement.result = {
                "success": obj.result == "correct" ? true : false,
                "duration": obj.latency,
                "response": obj.learner_response
            }

            statement.context.contextActivities.grouping[0].id = window.localStorage[this.activity];
            ADL.XAPIWrapper.sendStatement(statement);
        }
        else if (this.courseMode === 'scorm2004') {
            var api = getAPIHandle();
            // If the interaction id can't be found we'll add a new index of value count
            var index = findInteractionIndex(obj.id);
            index = index >= 0 ? index : api.GetValue("cmi.interactions._count");

            for (var key in obj) {
                var value = obj[key];
                if (key === "objectives") {
                    i = 0;
                    for (item in value) {
                        api.SetValue("cmi.interactions." + index + ".objectives." + i + ".id", item);
                        i++;
                    }
                }
                else if (key === "correct_responses") {
                    i = 0;
                    for (item in value) {
                        api.SetValue("cmi.interactions." + index + ".correct_responses." + i + ".pattern", item);
                        i++;
                    }
                }
                else {
                    api.SetValue("cmi.interactions." + index + "." + key, value);
                }
            }

            api.Commit("");
        }
    };

    XismBridge.prototype.GetInteractionObject = function (id) {
        var obj = {}, i;
        if (this.courseMode === 'xapi') {
            var verb = ADL.verbs.interacted;
            var statementsObject = ADL.XAPIWrapper.getStatements({"verb": verb.id});
            var singleStatement = statementsObject.statements[0];

            //Set up the object so that it matches the output for a SCORM interaction object
            obj.id = singleStatement.object.id;
            obj.type = singleStatement.object.definition.interactionType;
            obj.timestamp = singleStatement.timestamp;
            //obj.weighting = "none";
            obj.learner_response = singleStatement.result.response;
            obj.result = singleStatement.result.success ? "correct" : "incorrect";
            obj.latency = singleStatement.result.duration; // Maybe?
            obj.description = singleStatement.object.definition.description.en;
            obj.correct_responses = singleStatement.object.definition.correctResponsesPattern;
            obj.objectives = "none";

            return obj;
        }
        else if (this.courseMode === 'scorm2004') {
            var api = getAPIHandle();
            var index = findInteractionIndex(id);

            if (index >= 0) {
                obj.id = api.GetValue("cmi.interactions." + index + ".id");
                obj.type = api.GetValue("cmi.interactions." + index + ".type");
                obj.timestamp = api.GetValue("cmi.interactions." + index + ".timestamp");
                obj.weighting = api.GetValue("cmi.interactions." + index + ".weighting");
                obj.learner_response = api.GetValue("cmi.interactions." + index + ".learner_response");
                obj.result = api.GetValue("cmi.interactions." + index + ".result");
                obj.latency = api.GetValue("cmi.interactions." + index + ".latency");
                obj.description = api.GetValue("cmi.interactions." + index + ".description");

                var count = api.GetValue("cmi.interactions." + index + ".correct_responses._count");
                var responses = [];
                for (i = 0; i < count; i++) {
                    responses[i] = api.GetValue("cmi.interactions." + index + ".correct_responses." + i + ".pattern");
                }
                obj.correct_responses = responses;

                count = api.GetValue("cmi.interactions." + index + ".objectives._count");
                var objectives = [];
                for (i = 0; i < count; i++) {
                    objectives[i] = api.GetValue("cmi.interactions." + index + ".objectives." + i + ".id");
                }
                obj.objectives = objectives;
            }

            return obj;
        }
    };

    XismBridge.prototype.SetSuspendData = function (data) {
        if (this.courseMode === 'xapi') {
            ADL.XAPIWrapper.sendState(this.activity, this.agent, this.constants.activityStateIri, null, {suspend_data: [data]});
        }
        else if (this.courseMode === 'scorm2004') {
            var api = getAPIHandle();
            api.SetValue("cmi.suspend_data", data);
            api.Commit("");
        }
    };

    XismBridge.prototype.GetSuspendData = function () {
        if (this.courseMode === 'xapi') {
            var data = ADL.XAPIWrapper.getState(this.activity, this.agent, this.constants.activityStateIri);
            return data.suspend_data[0];
        }
        else if (this.courseMode === 'scorm2004') {
            var api = getAPIHandle();
            return api.GetValue("cmi.suspend_data");
        }
    };

    var findInteractionIndex = function (id) {
        var api = getAPIHandle();
        var count = api.GetValue("cmi.interactions._count");

        for (var i = 0; i < count; i++) {
            if (api.GetValue("cmi.interactions." + i + ".id") == id) {
                return i;
            }
        }

        return -1;
    };

    var generateUUID = function () {
        var d = new Date().getTime();

        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            var r = (d + Math.random() * 16) % 16 | 0;
            d = Math.floor(d / 16);
            return (c == 'x' ? r : (r & 0x7 | 0x8)).toString(16);
        });
    };

    var getBasicStatement = function (account, activity, courseId) {
        return {
            actor: {
                objectType: "Agent",
                account: account
            },
            verb: {},
            object: {
                objectType: "Activity",
                id: activity
            },
            context: {
                contextActivities: {
                    parent: [
                        {
                            id: courseId,
                            objectType: "Activity"
                        }
                    ],
                    grouping: [
                        {
                            id: "",
                            objectType: "Activity"
                        }
                    ]
                }
            }
        };
    };

    // -------------------------------------------------------
    // SCORM 2004 Helper functions.
    // -------------------------------------------------------
    var scormVersion = "2004";
    var SCORM_findAPITries = 0;
    var SCORM_objAPI = null;
    var windowObjectToFind = "";

    function updateObjectToFind() {
        if (scormVersion === "12") {
            windowObjectToFind = "API";
        }
        else {
            windowObjectToFind = "API_1484_11";
        }
    }
    updateObjectToFind();

    function getAPIHandle() {
        return SCORM_GrabAPI();
    }

    function SCORM_GrabAPI() {
        if (typeof(SCORM_objAPI) === "undefined" || SCORM_objAPI === null) {
            SCORM_objAPI = SCORM_GetAPI();
        }
        return SCORM_objAPI;
    }

    function SCORM_SearchForAPI(wndLookIn) {
        var objAPITemp = null;
        var strDebugID = "";

        strDebugID = "Name=" + wndLookIn.name + ", href=" + wndLookIn.location.href

        objAPITemp = eval("wndLookIn." + windowObjectToFind);

        if (SCORM_APIFound(objAPITemp)) {
            return objAPITemp;
        }

        if (SCORM_WindowHasParent(wndLookIn)) {
            objAPITemp = SCORM_SearchForAPI(wndLookIn.parent);
        }

        if (SCORM_APIFound(objAPITemp)) {
            return objAPITemp;
        }

        if (SCORM_WindowHasOpener(wndLookIn)) {
            objAPITemp = SCORM_SearchForAPI(wndLookIn.opener);
        }

        if (SCORM_APIFound(objAPITemp)) {
            return objAPITemp;
        }

        //look in child frames individually, don't call this function recursively
        //on them to prevent an infinite loop when it looks back up to the parents
        objAPITemp = SCORM_LookInChildren(wndLookIn);

        if (SCORM_APIFound(objAPITemp)) {
            return objAPITemp;
        }
        return null;
    }

    function SCORM_LookInChildren(wnd) {
        var objAPITemp = null;

        var strDebugID = "";

        strDebugID = "Name=" + wnd.name + ", href=" + wnd.location.href

        for (var i = 0; i < wnd.frames.length; i++) {

            WriteToDebug("Looking in child frame " + i);
            objAPITemp = eval("win.frames[" + i + "]." + windowObjectToFind);

            if (SCORM_APIFound(objAPITemp)) {
                return objAPITemp;
            }

            objAPITemp = SCORM_LookInChildren(wnd.frames[i]);

            if (SCORM_APIFound(objAPITemp)) {
                return objAPITemp;
            }
        }

        return null;
    }

    function SCORM_WindowHasOpener(wnd) {
        if ((wnd.opener != null) && (wnd.opener != wnd) && (typeof(wnd.opener) != "undefined")) {
            return true;
        }
        else {
            return false;
        }
    }

    function SCORM_WindowHasParent(wnd) {
        if ((wnd.parent != null) && (wnd.parent != wnd) && (typeof(wnd.parent) != "undefined")) {
            return true;
        }
        else {
            return false;
        }
    }

    function SCORM_APIFound(obj) {
        if (obj == null || typeof(obj) == "undefined") {
            return false;
        }
        else {
            return true;
        }
    }

    /*
     ScanParentsForApi
     -Searches all the parents of a given window until
     it finds an object named "API". If an
     object of that name is found, a reference to it
     is returned. Otherwise, this function returns null.
     */
    function SCORM_ScanParentsForApi(win) {
        /*
         Establish an outrageously high maximum number of
         parent windows that we are will to search as a
         safe guard against an infinite loop. This is
         probably not strictly necessary, but different
         browsers can do funny things with undefined objects.
         */
        var MAX_PARENTS_TO_SEARCH = 500;
        var nParentsSearched = 0;

        /*
         Search each parent window until we either:
         -find the API,
         -encounter a window with no parent (parent is null
         or the same as the current window)
         -or, have reached our maximum nesting threshold
         */
        while ((eval("win." + windowObjectToFind) == null || eval("win." + windowObjectToFind) === undefined) &&
        (win.parent != null) && (win.parent != win) &&
        (nParentsSearched <= MAX_PARENTS_TO_SEARCH)
            ) {

            nParentsSearched++;
            win = win.parent;
        }

        /*
         If the API doesn't exist in the window we stopped looping on,
         then this will return null.
         */
        return eval("win." + windowObjectToFind);
    }

    /*
     GetAPI
     -Searches all parent and opener windows relative to the
     current window for the SCORM API Adapter.
     Returns a reference to the API Adapter if found or null
     otherwise.
     */
    function SCORM_GetAPI() {
        var API = null;

        //Search all the parents of the current window if there are any
        if ((window.parent != null) && (window.parent != window)) {
            API = SCORM_ScanParentsForApi(window.parent);
        }

        /*
         If we didn't find the API in this window's chain of parents,
         then search all the parents of the opener window if there is one
         */
        if ((API == null) && (window.top.opener != null)) {
            API = SCORM_ScanParentsForApi(window.top.opener);
        }

        return API;
    }

    return XismBridge;
})();