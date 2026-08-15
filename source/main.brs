sub Main()
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.SetMessagePort(port)

    scene = screen.CreateScene("HomeScene")
    scene.ObserveField("exitRequested", port)
    screen.Show()
    scene.SetFocus(true)

    exitTimer = CreateObject("roTimespan")
    exitTimer.Mark()

    while true
        if exitTimer.TotalSeconds() >= 60
            screen.Close()
            return
        end if

        msg = wait(500, port)
        if msg <> invalid
            if type(msg) = "roSGScreenEvent"
                if msg.IsScreenClosed() then return
            else if type(msg) = "roSGNodeEvent"
                if msg.GetField() = "exitRequested" and msg.GetData() = true
                    screen.Close()
                    return
                end if
            end if
        end if
    end while
end sub
