sub init()
    m.video = m.top.findNode("video")
    m.overlay = m.top.findNode("overlay")
    m.panel = m.top.findNode("panel")
    m.title = m.top.findNode("title")
    m.status = m.top.findNode("status")
    m.details = m.top.findNode("details")
    m.urlValue = m.top.findNode("urlValue")
    m.help = m.top.findNode("help")
    m.exitTimer = m.top.findNode("exitTimer")
    m.rowBgs = [
        m.top.findNode("row0Bg")
        m.top.findNode("row1Bg")
        m.top.findNode("row2Bg")
        m.top.findNode("row3Bg")
    ]
    m.rowTexts = [
        m.top.findNode("row0Text")
        m.top.findNode("row1Text")
        m.top.findNode("row2Text")
        m.top.findNode("row3Text")
    ]
    m.config = GetDefaultStreamConfig()
    m.streamUrl = m.config.hlsUrl
    m.selectedRow = 0
    m.keyboardDialog = invalid
    m.registry = invalid
    m.didAutoPlay = false

    m.video.observeField("state", "onVideoStateChange")
    m.video.observeField("errorMsg", "onVideoError")
    m.exitTimer.observeField("fire", "onExitTimerFire")
    m.exitTimer.control = "start"
    m.top.setFocus(true)

    loadSavedConfig()
    showReady()
end sub

sub onExitTimerFire()
    m.video.control = "stop"
    m.top.exitRequested = true
    m.top.close = true
end sub

sub loadSavedConfig()
    runRegistryTask("load", "")
end sub

sub runRegistryTask(command as string, value as string)
    task = CreateObject("roSGNode", "RegistryTask")
    task.command = command
    task.value = value
    task.observeField("result", "onRegistryResult")
    task.control = "RUN"
    m.registry = task
end sub

sub onRegistryResult()
    result = m.registry.result
    if result = invalid then return

    if result.ok = false
        m.status.text = "Settings error"
        m.details.text = result.error
        return
    end if

    if result.command = "load"
        if result.value <> invalid and result.value <> ""
            m.streamUrl = result.value
        end if
        showReady()
        autoPlayOnStart()
    else if result.command = "save"
        m.streamUrl = result.value
        showReady()
        m.status.text = "URL saved"
        m.details.text = "Select Play stream, or relaunch the app to auto-play."
    else if result.command = "clear"
        m.streamUrl = m.config.hlsUrl
        showReady()
    end if
end sub

sub autoPlayOnStart()
    if m.didAutoPlay then return
    m.didAutoPlay = true

    if hasConfiguredUrl()
        playStream()
    end if
end sub

sub showReady()
    m.video.control = "stop"
    m.overlay.visible = true
    m.panel.visible = true
    m.title.text = m.config.title
    updateMenu()

    if not hasConfiguredUrl()
        m.status.text = "Bridge URL is not configured"
        m.details.text = "Select Edit HLS URL and enter the Home Assistant bridge URL."
    else
        m.status.text = "Ready"
        m.details.text = "Select Play stream to connect."
    end if

    m.urlValue.text = printableUrl()
end sub

sub playStream()
    if not hasConfiguredUrl()
        showReady()
        return
    end if

    videoContent = createObject("RoSGNode", "ContentNode")
    videoContent.url = m.streamUrl
    videoContent.title = m.config.title
    videoContent.streamFormat = "hls"
    videoContent.Live = true

    m.video.content = videoContent
    m.video.control = "play"
    m.overlay.visible = true
    m.panel.visible = true
    m.status.text = "Connecting..."
    m.details.text = "Opening live stream."
end sub

sub onVideoStateChange()
    state = m.video.state

    if state = "playing"
        m.status.text = "Playing live"
        m.overlay.visible = true
        m.panel.visible = true
        m.details.text = "Doorbell camera is live. Auto-exits after 1 minute."
    else if state = "buffering"
        m.overlay.visible = true
        m.panel.visible = true
        m.status.text = "Buffering..."
    else if state = "finished"
        m.overlay.visible = true
        m.panel.visible = true
        m.status.text = "Stream ended"
        m.details.text = "Press OK to reconnect."
    else if state = "error"
        showPlaybackError()
    end if
end sub

sub onVideoError()
    if m.video.state = "error" then showPlaybackError()
end sub

sub showPlaybackError()
    m.overlay.visible = true
    m.panel.visible = true
    m.status.text = "Playback error"

    errorText = m.video.errorMsg
    if errorText = invalid or errorText = ""
        errorText = "Roku could not play the HLS stream. Check that the bridge is running and that ffmpeg is producing H.264/AAC-compatible HLS."
    end if

    m.details.text = errorText + chr(10) + chr(10) + "Press OK to retry."
end sub

function hasConfiguredUrl() as boolean
    if m.streamUrl = invalid or m.streamUrl = "" then return false
    if instr(1, m.streamUrl, "YOUR_BRIDGE_IP") > 0 then return false
    return true
end function

function printableUrl() as string
    if m.streamUrl = invalid or m.streamUrl = "" then return "Not set"
    return m.streamUrl
end function

sub moveSelection(delta as integer)
    m.selectedRow = m.selectedRow + delta
    if m.selectedRow < 0
        m.selectedRow = 3
    else if m.selectedRow > 3
        m.selectedRow = 0
    end if
    updateMenu()
end sub

sub updateMenu()
    for i = 0 to 3
        if i = m.selectedRow
            m.rowBgs[i].color = "#2D7D46"
            m.rowBgs[i].opacity = 1
            m.rowTexts[i].color = "#FFFFFF"
        else
            m.rowBgs[i].color = "#1D2733"
            m.rowBgs[i].opacity = 0.72
            m.rowTexts[i].color = "#D8DEE9"
        end if
    end for
end sub

sub selectCurrentRow()
    if m.selectedRow = 0
        playStream()
    else if m.selectedRow = 1
        showUrlKeyboard()
    else if m.selectedRow = 2
        runRegistryTask("save", m.config.hlsUrl)
    else if m.selectedRow = 3
        runRegistryTask("clear", "")
    end if
end sub

sub showUrlKeyboard()
    dialog = CreateObject("roSGNode", "StandardKeyboardDialog")
    if dialog = invalid
        dialog = CreateObject("roSGNode", "KeyboardDialog")
    end if

    dialog.title = "HLS URL"
    dialog.message = ["Enter the Home Assistant HLS URL ending in stream.m3u8."]
    dialog.buttons = ["Save", "Cancel"]
    if hasConfiguredUrl()
        dialog.text = m.streamUrl
    else
        dialog.text = "http://192.168.10.104:8123/api/unifi_roku_bridge/"
    end if
    dialog.observeFieldScoped("buttonSelected", "onKeyboardButtonSelected")
    m.keyboardDialog = dialog
    m.top.dialog = dialog
end sub

sub onKeyboardButtonSelected()
    if m.keyboardDialog = invalid then return

    selected = m.keyboardDialog.buttonSelected
    if selected = 0
        value = m.keyboardDialog.text
        m.keyboardDialog.close = true
        m.keyboardDialog = invalid
        if value = ""
            m.status.text = "URL was not saved"
            m.details.text = "The HLS URL cannot be blank."
        else
            runRegistryTask("save", value)
        end if
    else if selected = 1
        m.keyboardDialog.close = true
        m.keyboardDialog = invalid
    end if
end sub

function onKeyEvent(key as string, press as boolean) as boolean
    if press = false then return false

    if key = "up"
        if m.overlay.visible then moveSelection(-1)
        return true
    else if key = "down"
        if m.overlay.visible then moveSelection(1)
        return true
    else if key = "OK"
        if m.overlay.visible
            selectCurrentRow()
        else
            m.overlay.visible = true
            m.panel.visible = true
        end if
        return true
    else if key = "play"
        playStream()
        return true
    else if key = "options"
        m.overlay.visible = not m.overlay.visible
        m.panel.visible = m.overlay.visible
        return true
    else if key = "back"
        if m.video.state = "playing" or m.video.state = "buffering"
            showReady()
            return true
        end if
    end if

    return false
end function
