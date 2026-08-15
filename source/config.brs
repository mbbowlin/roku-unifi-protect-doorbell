function GetDefaultStreamConfig() as object
    ' Set this to your bridge URL before packaging the Roku channel.
    return {
        title: "UniFi Protect Live"
        hlsUrl: "http://192.168.10.104:8123/api/unifi_roku_bridge/live.m3u8"
    }
end function
