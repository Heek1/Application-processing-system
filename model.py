class User:
    def __init__(self, tg_id, name):
        self.tg_id = tg_id
        self.name = name
        self.role = "client"

    def to_dict(self):
        return {
            "tg_id": self.tg_id,
            "name": self.name,
            "role": self.role
        }


class Client(User):
    def __init__(self, tg_id, name):
        super().__init__(tg_id, name)
        self.role = "client"


class Manager(User):
    def __init__(self, tg_id, name):
        super().__init__(tg_id, name)
        self.role = "manager"


class Admin(User):
    def __init__(self, tg_id, name):
        super().__init__(tg_id, name)
        self.role = "admin"


class RequestModel:
    def __init__(self, request_id, client_id, text):
        self.request_id = request_id
        self.client_id = client_id
        self.text = text
        self.status = "Нова"
        self.comments = []

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "client_id": self.client_id,
            "text": self.text,
            "status": self.status,
            "comments": self.comments
        }


class Comment:
    def __init__(self, req_id, user_id_tg, text, com_id):
        self.req_id = req_id
        self.user_id_tg = user_id_tg
        self.text = text
        self.com_id = com_id

    def to_dict(self):
        return {
            "com_id": self.com_id,
            "req_id": self.req_id,
            "user_id_tg": self.user_id_tg,
            "text": self.text
        }


class Msg:
    def __init__(self, msg_id, receiver_id, content):
        self.msg_id = msg_id
        self.receiver_id = receiver_id
        self.content = content

    def to_dict(self):
        return {
            "msg_id": self.msg_id,
            "receiver_id": self.receiver_id,
            "content": self.content
        }