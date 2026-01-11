var videoall_config = {
    // Tracking mode is:
    // "none" for no tracking
    // "scorm12" for SCORM 1.2
    // "scorm2004" for SCORM 2004
    // "xapi" for Tin Can/XAPI
    trackingMode: "scorm12",
    // Player type can be:
    // "youtube" for Youtube videos.  "url" is the ID of the Youtube video.
    // "vimeo" for Vimeo videos.  "url" is the ID of the Vimeo video.
    // "videojs" for local videos.  "url" is a URL to the video, relative or absolute.
    playerType: "vimeo",
    width: "100%",
    height: "100%",
    // Youtube
    //url: "M7lc1UVf-VE",
    // Vimeo
    //url: "42372767",
    // Videojs (relative, to the root of the package)
    //url: "file.mp4",
    // Videojs (absolute)
    //url: "http://video-js.zencoder.com/oceans-clip.mp4",
    url: "1110267241",
    
    autoplay: true,
    seekModeIncomplete: "ONLY_BACKWARD", // NONE, ANYWHERE, ONLY_BACKWARD
    seekModeCompleted: "ANYWHERE", // NONE, ANYWHERE, ONLY_BACKWARD
    bookmarkQuestion: "Would you like to return to your bookmark?",
    bookmarkForceResume: true,
    completionBy: "END", // END, PERCENT_WATCHED
    completionFraction: 1,
    completeFn: function() {
        // console.log("Perform custom completion activities here.");
    },
    tracks: [
        
    ],
    poster: ""
};
