# SCORM 1.2 Generator Wizard v0.3

![Alt text](/SCORM-GW-logo-150px.webp?raw=true  "SCORM Generator Wizard v0.3 logo")

A simple SCORM wrapper for Windows.
Supported Host/Media: Vimeo, YouTube, Remote URL and local file (tested with .mp4)

Single mode or batch mode using .csv. A blank template is supplied within the repo (template-csv.csv). Csv headers order is "title, description, path_or_url"

## Requirements
- Windows 11
- Python >= 3.12 (not tested on other version)

## How to build it 
Run 'build.bat' (it takes a while) and in /dist/ folder you'll find the all bundled .exe file that you can move where you prefer. You just need the .exe after the build. 

Vibe-coded in Python with Cursor IDE.

## TO-DO List:
- add subtitle (.srt? .vvt?) files (in batch mode too)
