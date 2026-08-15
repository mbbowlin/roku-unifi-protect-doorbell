sub Main()
    screen = CreateObject("roSGScreen")
    port = CreateObject("roMessagePort")
    screen.SetMessagePort(port)

    scene = screen.CreateScene("HomeScene")
    scene.ObserveField("exitRequested", port)
    screen.Show()

    while true
        msg = wait(0, port)
        if type(msg) = "roSGScreenEvent"
            if msg.IsScreenClosed() then return
        else if type(msg) = "roSGNodeEvent"
            if msg.GetField() = "exitRequested" and msg.GetData() = true
                screen.Close()
                return
            end if
        end if
    end while
end sub
