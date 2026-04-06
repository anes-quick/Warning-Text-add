@echo off
setlocal enabledelayedexpansion

:: Set up the output folder
set "output_dir=output"
echo Checking if output folder exists...
mkdir "%output_dir%"

:: List of backgrounds, overlays, and audios
set "backgrounds_part1=background1.mp4 background2.mp4 background3.mp4 background4.mp4 background5.mp4"
set "backgrounds_part2=background6.mp4 background7.mp4 background8.mp4 background9.mp4 background10.mp4"

set "overlays_part1=overlay1.png overlay2.png overlay3.png overlay4.png overlay5.png"
set "overlays_part2=overlay6.png overlay7.png overlay8.png overlay9.png overlay10.png"

set "audios_part1=music1.mp3 music2.mp3 music3.mp3 music4.mp3 music5.mp3"
set "audios_part2=music6.mp3 music7.mp3 music8.mp3 music9.mp3 music10.mp3"

:: Load overlay names from text file
echo Loading overlay names from overlay_names.txt...
if not exist "overlay_names.txt" (
    echo ERROR: overlay_names.txt not found!
    echo Please create overlay_names.txt with one overlay name per line.
    pause
    exit /b
)

set overlay_name_counter=1
for /f "usebackq delims=" %%a in ("overlay_names.txt") do (
    set "overlay!overlay_name_counter!_name=%%a"
    set /a overlay_name_counter+=1
)

echo Loaded !overlay_name_counter! overlay names from file.

:: Initialize a counter for unique file names
set file_counter=1

:: Function to process one batch of files
call :process_batch "backgrounds_part1" "overlays_part1" "audios_part1" "batch1"
call :process_batch "backgrounds_part2" "overlays_part2" "audios_part2" "batch2"

:: Final message
echo Done creating videos!
pause
exit /b

:process_batch
setlocal enabledelayedexpansion

:: Load parameters
set "backgrounds=!%~1!"
set "overlays=!%~2!"
set "audios=!%~3!"
set "batch_name=%~4"

echo Processing batch: !batch_name!

:: Convert the lists into arrays
set idx=0
for %%B in (!backgrounds!) do (
    set "background[!idx!]=%%B"
    set /a idx+=1
)

set idx=0
for %%P in (!overlays!) do (
    set "overlay[!idx!]=%%P"
    set /a idx+=1
)

set idx=0
for %%A in (!audios!) do (
    set "audio[!idx!]=%%A"
    set /a idx+=1
)

:: Loop through each overlay
for /L %%i in (0,1,4) do (
    set "current_overlay=!overlay[%%i]!"

    :: Extract the custom name for this overlay
    for %%N in (1 2 3 4 5 6 7 8 9 10) do (
        if "!current_overlay!" == "overlay%%N.png" set "overlay_name=!overlay%%N_name!"
    )

    :: Loop through each background and each audio
    for /L %%j in (0,1,4) do (
        set "current_background=!background[%%j]!"
        set "current_audio=!audio[%%j]!"

        :: Set the output file name with unique counter
        set "output_file=%output_dir%\!overlay_name!_!file_counter!.mp4"
        echo Creating video: !output_file!

        :: Check if files exist
        if not exist "!current_background!" (
            echo ERROR: Background file !current_background! not found.
            exit /b
        )
        if not exist "!current_overlay!" (
            echo ERROR: Overlay file !current_overlay! not found.
            exit /b
        )
        if not exist "!current_audio!" (
            echo ERROR: Audio file !current_audio! not found.
            exit /b
        )

        :: Run FFmpeg to create the video (force video to 6 seconds, and audio to 6 seconds with reduced volume)
        ffmpeg -y -i "!current_background!" -i "!current_overlay!" -i "!current_audio!" -filter_complex "[0:v]scale=1080:1920,setsar=1[bg];[1:v]scale=1080:1920,setsar=1[overlay];[bg][overlay]overlay=0:0[vid];[vid]format=yuv420p,trim=duration=6[v];[2:a]atrim=duration=6,volume=0.1[a]" -map "[v]" -map "[a]" -c:v libx264 -c:a aac -t 6 "!output_file!"

        echo Created video: !output_file!
        set /a file_counter+=1
    )
)

exit /b
