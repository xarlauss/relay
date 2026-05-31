import asyncio      #асинхронный код
import websockets   #соединение
import json         #понимать команды
import socket       #magic packet

password = "jftoip"
PORT = 9876

pc_connect = None       #проверка соединений
phone_connect = None
pc_input_ws = None
phone_input_ws = None

async def new_conn(ws):                 #кто то подключается, основная функция
    msg = json.loads(await ws.recv())
    if msg["secret"] != password:
            await ws.send(json.dumps({"type": "nope"}))
            return
    await ws.send(json.dumps({"type": "ok"}))   #обрывает бесконечные запросы
    if msg["role"] == "phone":  #клииент - телефон
        await phone_loop(ws)
    elif msg["role"] == "pc":   #клиент - пк
        await pc_loop(ws)
    elif msg["role"] == "phone_input":
        await phone_input_loop(ws)
    elif msg["role"] == "pc_input":
        await pc_input_loop(ws)
    elif msg["role"] == "phone_status":
        await phone_status_loop(ws)

def wol(mac, bcast="rakulovsftp.ddns.net"):    
     print(f"отправляю WoL на {bcast}")#собираем magic packet
    m = mac.replace(":", "").replace("-", "")
    pkt = b"\xff" * 6 + bytes.fromhex(m) * 16
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.sendto(pkt, (bcast, 40000))
    s.close()
    print("WoL отправлен")

async def phone_input_loop(ws):
    global phone_input_ws
    phone_input_ws = ws
    async for msg in ws:
        if pc_input_ws:
            await pc_input_ws.send(msg)

async def pc_input_loop(ws):
    global pc_input_ws
    pc_input_ws = ws
    try:
        async for msg in ws:
            pass
    except:
        pass
    finally:
        pc_input_ws = None
        

async def phone_loop(ws):   #цикл работы с телефоном
    global phone_connect
    phone_connect = ws
    async for msg in ws:    #вечный цикл принятия команд
        msg = json.loads(msg)   #превращает строку в json
        if msg["type"] == "wake":   #еслии будим пк - отправить magic packet
            wol(msg["mac"])
        elif msg["type"] == "mm":       #mouse moving
            if pc_connect:
                await pc_connect.send(json.dumps(msg))
        elif msg["type"] == "mc":
            if pc_connect:
                await pc_connect.send(json.dumps(msg))
        elif msg["type"] == "status_check":
            await ws.send(json.dumps({"type": "status", "on": pc_connect is not None}))

async def phone_status_loop(ws):
    async for msg in ws:
        msg = json.loads(msg)
        if msg["type"] == "status_check":
            await ws.send(json.dumps({"type": "status", "on": pc_connect is not None}))

async def pc_loop(ws):  #цикл работы с пк
    global pc_connect
    pc_connect = ws
    async for msg in ws:    #вечный цикл принятия команд
        if isinstance(msg, bytes):
            if phone_connect:
                await phone_connect.send(msg)
            continue
        msg = json.loads(msg)   #превращает строку в json
        if msg["type"] == "ping":   #проверка соединения
            await ws.send(json.dumps({"type": "pong"}))
        if msg["type"] == "frame":  #кадр который нужно перекинуть телефону
            if phone_connect:       #проверка что есть коннект
                await phone_connect.send(json.dumps(msg))

async def main():
    async with websockets.serve(new_conn, "0.0.0.0", PORT):
        await asyncio.Future()

asyncio.run(main())


