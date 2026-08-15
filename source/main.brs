sub Main()
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.SetMessagePort(port)

    scene = screen.CreateScene("HomeScene")
    scene.ObserveField("exitRequested", port)
    exitSignal = scene.findNode("exitSignal")
    if exitSignal <> invalid
        exitSignal.ObserveField("text", port)
    end if
    screen.Show()

    while true
        msg = wait(0, port)
        if type(msg) = "roSGScreenEvent"
            if msg.IsScreenClosed() then return
        else if type(msg) = "roSGNodeEvent"
            if msg.GetField() = "exitRequested" and msg.GetData() = true
                screen.Close()
                return
            else if msg.GetField() = "text" and msg.GetData() = "exit"
                screen.Close()
                return
            end if
        end if
    end while
end sub
