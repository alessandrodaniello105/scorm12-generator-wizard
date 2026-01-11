//$(function() {
//    $.blockUI({message: "<h2>Please wait, loading...</h2>"});
//});

var videoall = {
    config: videoall_config,
    completionAchieved: false,
    onComplete: function() {
        if (videoall.config.completeFn) {
            videoall.config.completeFn();
            var curPlayer = videoall[videoall.config.playerType];
            if (curPlayer.refreshPlayerDueToCompletion) {
                curPlayer.refreshPlayerDueToCompletion();
            }
        }
    },
    checkComplete: function() {
        var curPlayer = videoall[videoall.config.playerType];
        if (curPlayer.ready && !videoall.completionAchieved) {
            if (videoall.config.completionBy == "END") {
                // Do nothing, the end event will call the appropriate function.
            }
            else if (videoall.config.completionBy == "PERCENT_WATCHED") {
                if (curPlayer.getCurrentTime() / curPlayer.getDuration() >= videoall.config.completionFraction) {
                    videoall.setCompleted();
                }
            }
        }
    },
    setCompleted: function() {
        if (!videoall.completionAchieved) {
            videoall.completionAchieved = true;
            bridge.SetSuccessStatus("passed");
            bridge.SetCompletionStatus("completed");
            videoall.onComplete();
        }
    },
    checkBookmark: function() {
        var bookmark = bridge.GetBookmark();
        var restoreBookmark = false;
        if (bookmark) {
            if (videoall.config.bookmarkForceResume) {
                videoall[videoall.config.playerType].restoreFromBookmark(bookmark, true);
            }
            else if (confirm(videoall.config.bookmarkQuestion)) {
                videoall[videoall.config.playerType].restoreFromBookmark(bookmark, false);
            }
        }
    },
    onEnded: function() {
        if (videoall.config.completionBy == "END") {
            videoall.setCompleted();
        }
    }
};

var bridge = new XismBridge();
bridge.SetMode(videoall.config.trackingMode);
bridge.StartCourse("");
if (bridge.GetCompletionStatus() !== "completed") {
    bridge.SetCompletionStatus("incomplete");
    bridge.SetSuccessStatus("unknown")
} else {
    // Don't set the completion again if we've already set it.
    videoall.completionAchieved = true;
}

function updateBookmark() {
    if (videoall.config.playerType && videoall[videoall.config.playerType]) {
        videoall[videoall.config.playerType].updateBookmark();
    }
}

function start() {
    videoall[videoall.config.playerType].init();
    setInterval(function() {
        updateBookmark();
    }, 5000);
    if (videoall.config.completionBy == "PERCENT_WATCHED") {
        setInterval(function() {
            videoall.checkComplete();
        }, 100);
    }
}

// Returns true if the course is not expired or there is no expiration.
// Returns false if the course is expired.
function verifyExpiration() {
    var d = new Date();
    var n = d.getTime();
    if (videoall.config.expirationDate && videoall.config.expirationDate != -1) {
        if (videoall.config.expirationDate > n) {
            return false;
        }
    }
    return true;
}

function startAfterLicenseCheck() {
    if (videoall.config.licenseCheckUrl) {
        $.ajax({
            url: videoall.config.licenseCheckUrl,
            method: "GET",
            dataType: "jsonp"
        })
            .success(function(d) {
                if (d == true) {
                    start();
                }
                else {
                    alert("All seat licenses have been used.");
                }
            })
            .error(function() {
                alert("Seat license was unable to be checked, please contact an administrator.");
            });
    }
    else {
        start();
    }
}

$(function() {
    if (verifyExpiration()) {
        startAfterLicenseCheck();
    }
    else {
        alert("Access to this video has expired.");
    }
});
