#
# Серверное приложение для соединений
# https://github.com/karpov-dmitry-py/async-messenger.git
#
import asyncio
from asyncio import transports

class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):
        # print(data)

        decoded = data.decode().replace("\r\n", "")
        if not decoded:
            return

        if self.login is not None:
            self.send_message(decoded)
        else:
            if decoded.startswith("login:"):

                login = decoded.replace("login:", "").replace("\r\n", "")
                if any(client.login == login for client in self.server.clients):
                    self.transport.write(f"Логин {login} занят. Попробуйте другой!\n".encode())
                    asyncio.sleep(5) # даем время прочитать сообщение перед разрывом соединения - актуально для putty
                    self.transport.close()

                self.login = login
                self.transport.write(f"Привет, {self.login}!\r\n".encode())
                self.send_history()
            else:
                self.transport.write("Неправильный логин\r\n".encode())

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print("Пришел новый клиент")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Клиент вышел")

    def send_message(self, content: str):

        message = f"{self.login}: {content}\r\n"
        self.server.history.append(message)

        for user in self.server.clients:
            user.transport.write(message.encode())

    def send_history(self, depth: int=10):

        history = self.server.history
        if not history:
            return

        depth = min(depth, len(history))
        self.transport.write(f"{self.login}, вот последние {depth} сообщений в нашем чате:\r\n".encode())
        history_to_show = history[-1:-depth-1:-1]
        for message in history_to_show:
            self.transport.write(message.encode())

class Server:
    clients: list
    history: list

    def __init__(self):
        self.clients = []
        self.history = []

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()

process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")
