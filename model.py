class User:
    def __init__(self, tg_id, name, role):
        self.tg_id = tg_id
        self.name = name
        self.role = role
    def to_dict(self):
        return{
            'tg_id':self.tg_id,
            'full_name':self.name,
            'role':self.role
        }
class Request:
    def __init__(self, request_id, client_id, text):
        self.request_id = request_id
        self.client_id = client_id
        self.text = text
        self.status = "Нова"
        self.comments = []
    def to_dict(self):
        return{
            'request_id':self.request_id,
            'client_id':self.client_id,
            'text':self.text,
            'status':self.status
        }
class Comment:
    def __init__(self, req_id, user_id_tg, text, com_id):
        self.req_id = req_id
        self.user_id_tg = user_id_tg
        self.text = text
        self.com_id = com_id
    def to_dict(self):
        return {
            "req_id": self.req_id,
            "user_id_tg": self.user_id_tg,
            "text": self.text,
            "com_id": self.com_id
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