package main

import (
    "net"
    "bufio"
    "strconv"
    "fmt"
)

const PORT = 3540

func main() {
    //Listen создаёт сервер
    server, err := net.Listen("tcp", ":" + strconv.Itoa(PORT))
    if server == nil {
        panic("couldn't start listening: " + err.Error())
    }
    //clientConns() создаёт канал для хранения входящих соединений
    conns := clientConns(server) 
    for {
        go handleConn(<-conns) //если можно извлечь из канала соединение, то делаем это и обрабатываем его
    }
}

func clientConns(listener net.Listener) chan net.Conn {
    ch := make(chan net.Conn)
    i := 0  //счётчик входящих соединений
    go func() { //запускаем горутину
        for { 
            //Accept - принимает соединение
            clientConn, err := listener.Accept()
            if clientConn == nil {
                fmt.Printf("couldn't accept: " + err.Error())
                continue
            }
            i++
            fmt.Printf("Client %d with address %v connected to the address %v\n", 
                        i+1, clientConn.LocalAddr(), clientConn.RemoteAddr())
            ch <- clientConn
        }
    }()
    return ch
}

func handleConn(client net.Conn) {
    //буферизированный читатель данных из соединения с клиентом
    b := bufio.NewReader(client)
    for {
        line, err := b.ReadBytes('\n')
        if err != nil { // EOF, or worse
            break
        }
        client.Write(line) //посылаем обратно клиенту
    }
}
