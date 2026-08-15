sub init()
    m.top.functionName = "run"
end sub

sub run()
    command = m.top.command
    response = {
        command: command
        ok: true
        value: ""
        error: ""
    }

    section = CreateObject("roRegistrySection", "UniFiRokuBridge")
    if section = invalid
        response.ok = false
        response.error = "Could not open Roku registry."
        m.top.result = response
        return
    end if

    if command = "load"
        if section.Exists("hlsUrl")
            response.value = section.Read("hlsUrl")
        end if
    else if command = "save"
        value = m.top.value
        if value <> ""
            section.Write("hlsUrl", value)
        else if section.Exists("hlsUrl")
            section.Delete("hlsUrl")
        end if
        section.Flush()
        response.value = value
    else if command = "clear"
        if section.Exists("hlsUrl")
            section.Delete("hlsUrl")
            section.Flush()
        end if
    else
        response.ok = false
        response.error = "Unknown registry command."
    end if

    m.top.result = response
end sub
