package main

import (
    "net"
    "bufio"
    "strconv"
    "fmt"
    "sort"
    "io/ioutil"
    "strings"
    "gonum.org/v1/gonum/mat"
    "os"
    "errors"
)

const PORT      = 3540
const WORDLIST  = "words.txt"
const CLASSLIST = "classes.txt"
const WEIGHTS   = "weights.txt"

var err error
var classes []string
var words   []string
var weights *mat.Dense
var parametersLoaded bool = false


func ReadWords(file string) ([] string, error) { 
    b, err := ioutil.ReadFile(file) 
    if err != nil {
        return nil, err
    }
    content := string(b) 
    return strings.Fields(content), nil
} 
    
func ReadMatrix(file string) (*mat.Dense, error) {
    b, err := ioutil.ReadFile(file) 
    if err != nil {
        return nil, err
    }
    lines := strings.Split(string(b), "\n")
	nums := make([]float64, 0, len(lines))
	rows := 0
	for _, l := range lines {
		if len(l) == 0 {
			continue
		}
		rows++
		snumbers := strings.Fields(l)
		for _, sn := range snumbers {
			n, err := strconv.ParseFloat(sn, 64)
			if err != nil {
				return nil, err
			}
			nums = append(nums, n)
		}
	}
	return mat.NewDense(rows, len(strings.Fields(lines[0])), nums), nil
}

func LoadParameters() error {
    // ПЫТАЕМСЯ ПРОЧЕСТЬ МОДЭЛЬ
    if words, err = ReadWords(WORDLIST); err != nil { 
        return errors.New("Ошибка загрузки списка слов!\n" + err.Error())
    }  
    if classes, err = ReadWords(CLASSLIST); err != nil {
        return errors.New("Ошибка загрузки списка классов!\n" + err.Error())
    }
    if weights, err = ReadMatrix(WEIGHTS); err != nil {
        return errors.New("Ошибка загрузки матрицы классификатора!\n" + err.Error())
    }
 
    w_r, w_c := weights.Dims()
    wo_n, cl_n := len(words), len(classes)
    
    if w_r != cl_n {
        return errors.New(fmt.Sprintf(
            "Размеры ваших файлов не равны (число классов в списке = %d, в матрице весов = %d).\n", cl_n, w_r))
    }
    if w_c != wo_n {
        return errors.New(fmt.Sprintf(
            "Размеры ваших файлов не равны (число слов в списке = %d, в матрице весов = %d).\n", wo_n, w_c))
    }
    parametersLoaded = true
    return nil
}

func WriteStringToFile(file string, content string, append_mode bool) {
	
	var f *os.File
	var err error
	if append_mode {
	    f, err = os.OpenFile(file, os.O_APPEND|os.O_WRONLY, 0644) 
	} else {
	    f, err = os.Create(file)
	}
	if err != nil {
        panic("Невозможно открыть файл для записи!\n" + err.Error())
    }
    defer f.Close()

    _, err = f.WriteString(content)
    if err != nil {
        panic("Невозможно записать информацию в файл!\n" + err.Error())
    }
}


func ClientConns(listener net.Listener) chan net.Conn {
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
            //fmt.Printf("Client %d with address %v connected to the address %v\n", 
            //            i, clientConn.LocalAddr(), clientConn.RemoteAddr())
            ch <- clientConn
        }
    }()
    return ch
}

func HandleConn(client net.Conn) {
    //буферизированный читатель данных из соединения с клиентом
    b := bufio.NewReader(client)
    SendToClient := func ( msg string ) { client.Write([]byte(msg)) }
    
    for {
        line, err := b.ReadString('\n')
        if err != nil { // EOF, or worse
            SendToClient("Error")
            break
        }
        //fmt.Printf("%T - %v, %T - %v", line, line, err, err)  
        switch line {
        case "CLASSIFY\n":
            if parametersLoaded {
                //SendToClient("Ожидаю строку для классификации")
                stems, err2 := b.ReadString('\n')
                if err2 != nil { // EOF, or worse
                    SendToClient("Invalid parameters\n")
                    break
                }
                SendToClient(Classify(stems))
            } else {
                //TODO нормально отправлять ошибку
                SendToClient("ERROR: SERVER IS NOT READY\n")
            }
        case "UPDATE\n": 
            //1. список слов
            words, err2 := b.ReadString('\n')
            if err2 != nil { // EOF, or worse
                SendToClient("Invalid parameters\n")
                break
            }
            WriteStringToFile(WORDLIST, words, false)
            
            //2. список классов
            classes, err3 := b.ReadString('\n')
            if err3 != nil { // EOF, or worse
                SendToClient("Invalid parameters\n")
                break
            }
            WriteStringToFile(CLASSLIST, classes, false)
            
            //3. матрица весов размером (2.) * (1.)
            WriteStringToFile(WEIGHTS, "", false)
            for {
                wts, err4 := b.ReadString('\n')
                if len(wts) == 1 || err4 != nil { // EOF, or worse
                    break
                }
                WriteStringToFile(WEIGHTS, wts, true)
            }
            err = LoadParameters()
            if err != nil {
                SendToClient("ERROR: UPLOADED PARAMETERS WERE NOT LOADED CORRECTLY\n")
                fmt.Println("Параметры классификатора не загружены. Обновите их с помощью команды UPDATE")
            } else {
                SendToClient("updated\n")
                fmt.Println("Параметры классификатора успешно обновлены. Сервер готов к работе!")
            }
        default:
            SendToClient("Invalid command\n")
        }
        
    }
}

func Classify(content string) string {
    counts := make([]float64, len(words))
    stems := strings.Fields(content)
    fmt.Println(stems)
    for _, st := range(stems) {
        i := sort.Search(len(words), func(i int) bool { return words[i] >= st })
        if i < len(words) && words[i] == st{
	        counts[i]++  
        } 
    }
    counts_mat := mat.NewVecDense(len(words), counts)

    var res mat.Dense
    res.Mul(weights, counts_mat)
    
    min := res.At(0, 0)
    min_i := 0
    for i := 0; i < len(classes); i++ {
        if res.At(i, 0) < min {
            min = res.At(i, 0)
            min_i = i 
        }
    }

    //fmt.Println(counts)
    //fmt.Println(counts_mat)
    //fmt.Println(res)
    //fmt.Println(classes[min_i])    
    return classes[min_i]
}


func main() {
    //Listen создаёт сервер
    server, err := net.Listen("tcp", ":" + strconv.Itoa(PORT))
    if server == nil {
        panic("couldn't start listening: " + err.Error())
    }
    
    err = LoadParameters()
    if err != nil {
        fmt.Println("Параметры классификатора не загружены. Обновите их с помощью команды UPDATE")
    } else {
        fmt.Println("Параметры классификатора успешно загружены. Сервер готов к работе!")
    }
    
    //clientConns() создаёт канал для хранения входящих соединений
    conns := ClientConns(server) 
    for {
        go HandleConn(<-conns) //если можно извлечь из канала соединение, то делаем это и обрабатываем его
    }
}
