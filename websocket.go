package main

// ==================== IMPLEMENTACIÓN WEBSOCKET PURO (RFC 6455) ====================
// Sin librerías externas - Solo biblioteca estándar de Go

import (
	"bufio"
	"crypto/sha1"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

const websocketGUID = "258EAFA5-E914-47DA-95CA-5549C5AD8BE7"

// Opcodes WebSocket
const (
	opContinuation = 0x0
	opText         = 0x1
	opBinary       = 0x2
	opClose        = 0x8
	opPing         = 0x9
	opPong         = 0xA
)

// WSConn representa una conexión WebSocket
type WSConn struct {
	conn     net.Conn
	reader   *bufio.Reader
	muWrite  sync.Mutex
	cerrado  bool
	muCerrar sync.Mutex
}

// AceptarWebSocket realiza el handshake HTTP→WebSocket
func AceptarWebSocket(w http.ResponseWriter, r *http.Request) (*WSConn, error) {
	if !strings.EqualFold(r.Header.Get("Upgrade"), "websocket") {
		return nil, errors.New("no es una solicitud WebSocket")
	}

	key := r.Header.Get("Sec-WebSocket-Key")
	if key == "" {
		return nil, errors.New("falta Sec-WebSocket-Key")
	}

	// Calcular clave de aceptación
	h := sha1.New()
	h.Write([]byte(key + websocketGUID))
	accept := base64.StdEncoding.EncodeToString(h.Sum(nil))

	// Hijack de la conexión HTTP
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		return nil, errors.New("servidor no soporta hijacking")
	}

	conn, bufrw, err := hijacker.Hijack()
	if err != nil {
		return nil, err
	}

	// Enviar respuesta de upgrade
	respuesta := "HTTP/1.1 101 Switching Protocols\r\n" +
		"Upgrade: websocket\r\n" +
		"Connection: Upgrade\r\n" +
		"Sec-WebSocket-Accept: " + accept + "\r\n\r\n"

	_, err = bufrw.WriteString(respuesta)
	if err != nil {
		conn.Close()
		return nil, err
	}
	err = bufrw.Flush()
	if err != nil {
		conn.Close()
		return nil, err
	}

	return &WSConn{
		conn:   conn,
		reader: bufrw.Reader,
	}, nil
}

// leerFrame lee un frame WebSocket completo
func (ws *WSConn) leerFrame() (opcode byte, payload []byte, err error) {
	// Byte 1: FIN + opcode
	header := make([]byte, 2)
	if _, err = io.ReadFull(ws.reader, header); err != nil {
		return 0, nil, err
	}

	// fin := (header[0] & 0x80) != 0
	opcode = header[0] & 0x0F
	masked := (header[1] & 0x80) != 0
	payloadLen := uint64(header[1] & 0x7F)

	// Longitud extendida
	switch payloadLen {
	case 126:
		extLen := make([]byte, 2)
		if _, err = io.ReadFull(ws.reader, extLen); err != nil {
			return 0, nil, err
		}
		payloadLen = uint64(binary.BigEndian.Uint16(extLen))
	case 127:
		extLen := make([]byte, 8)
		if _, err = io.ReadFull(ws.reader, extLen); err != nil {
			return 0, nil, err
		}
		payloadLen = binary.BigEndian.Uint64(extLen)
	}

	// Máscara (cliente → servidor siempre enmascarado)
	var maskKey [4]byte
	if masked {
		if _, err = io.ReadFull(ws.reader, maskKey[:]); err != nil {
			return 0, nil, err
		}
	}

	// Payload
	payload = make([]byte, payloadLen)
	if payloadLen > 0 {
		if _, err = io.ReadFull(ws.reader, payload); err != nil {
			return 0, nil, err
		}
	}

	// Desenmascarar
	if masked {
		for i := range payload {
			payload[i] ^= maskKey[i%4]
		}
	}

	return opcode, payload, nil
}

// escribirFrame escribe un frame WebSocket (servidor → cliente, sin máscara)
func (ws *WSConn) escribirFrame(opcode byte, payload []byte) error {
	ws.muWrite.Lock()
	defer ws.muWrite.Unlock()

	ws.muCerrar.Lock()
	if ws.cerrado {
		ws.muCerrar.Unlock()
		return errors.New("conexión cerrada")
	}
	ws.muCerrar.Unlock()

	var frame []byte
	payloadLen := len(payload)

	// Byte 1: FIN=1 + opcode
	frame = append(frame, 0x80|opcode)

	// Longitud del payload
	if payloadLen <= 125 {
		frame = append(frame, byte(payloadLen))
	} else if payloadLen <= 65535 {
		frame = append(frame, 126)
		lenBytes := make([]byte, 2)
		binary.BigEndian.PutUint16(lenBytes, uint16(payloadLen))
		frame = append(frame, lenBytes...)
	} else {
		frame = append(frame, 127)
		lenBytes := make([]byte, 8)
		binary.BigEndian.PutUint64(lenBytes, uint64(payloadLen))
		frame = append(frame, lenBytes...)
	}

	// Payload (sin máscara para servidor → cliente)
	frame = append(frame, payload...)

	// Establecer deadline de escritura
	ws.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
	_, err := ws.conn.Write(frame)
	return err
}

// ReadMessage lee un mensaje JSON del WebSocket y lo parsea
// Maneja frames de control (ping, pong, close) internamente
func (ws *WSConn) ReadMessage() (map[string]interface{}, error) {
	for {
		opcode, payload, err := ws.leerFrame()
		if err != nil {
			return nil, err
		}

		switch opcode {
		case opText, opBinary:
			var datos map[string]interface{}
			if err := json.Unmarshal(payload, &datos); err != nil {
				return nil, err
			}
			return datos, nil
		case opPing:
			ws.escribirFrame(opPong, payload)
		case opPong:
			// Ignorar pong
		case opClose:
			ws.escribirFrame(opClose, payload)
			return nil, errors.New("conexión cerrada por el cliente")
		}
	}
}

// SendJSON envía un objeto como JSON por WebSocket
func (ws *WSConn) SendJSON(v interface{}) error {
	datos, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return ws.escribirFrame(opText, datos)
}

// SendPing envía un ping al cliente
func (ws *WSConn) SendPing() error {
	return ws.escribirFrame(opPing, []byte{})
}

// Close cierra la conexión WebSocket
func (ws *WSConn) Close() {
	ws.muCerrar.Lock()
	defer ws.muCerrar.Unlock()
	if !ws.cerrado {
		ws.cerrado = true
		ws.escribirFrame(opClose, []byte{})
		ws.conn.Close()
	}
}

// ==================== GESTOR DE CLIENTES WEBSOCKET ====================

// GestorClientes maneja todos los clientes WebSocket conectados
type GestorClientes struct {
	mu       sync.RWMutex
	clientes map[*WSConn]bool
}

// NuevoGestorClientes crea un nuevo gestor de clientes WebSocket
func NuevoGestorClientes() *GestorClientes {
	return &GestorClientes{
		clientes: make(map[*WSConn]bool),
	}
}

// Agregar registra un nuevo cliente WebSocket
func (g *GestorClientes) Agregar(ws *WSConn) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.clientes[ws] = true
}

// Eliminar remueve un cliente WebSocket
func (g *GestorClientes) Eliminar(ws *WSConn) {
	g.mu.Lock()
	defer g.mu.Unlock()
	delete(g.clientes, ws)
}

// CantidadClientes retorna el número de clientes conectados
func (g *GestorClientes) CantidadClientes() int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return len(g.clientes)
}

// CerrarTodos cierra todas las conexiones WebSocket
func (g *GestorClientes) CerrarTodos() {
	g.mu.Lock()
	defer g.mu.Unlock()
	for cliente := range g.clientes {
		cliente.Close()
		delete(g.clientes, cliente)
	}
}

// BroadcastJSON envía un mensaje JSON a todos los clientes conectados
func (g *GestorClientes) BroadcastJSON(v interface{}) {
	g.mu.RLock()
	defer g.mu.RUnlock()

	for cliente := range g.clientes {
		if err := cliente.SendJSON(v); err != nil {
			log.Printf("Error enviando a cliente: %v", err)
		}
	}
}

// IniciarHeartbeat envía pings periódicos a todos los clientes (cada 30s)
func (g *GestorClientes) IniciarHeartbeat() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		g.mu.RLock()
		for cliente := range g.clientes {
			if err := cliente.SendPing(); err != nil {
				log.Printf("Error en heartbeat: %v", err)
			}
		}
		g.mu.RUnlock()
	}
}
