class User:
    def __init__(self, user_id, name, role):
        self.user_id = user_id
        self.name = name
        self.role = role
class Request:
    def __init__(self, request_id, client_id, text):
        self.request_id = request_id
        self.client_id = client_id
        self.text = text
        self.status = "Нова"
        self.comments = []
class Comment:
    def __init__(self, author_name, text):
        self.author_name = author_name
        self.text = text
class Msg:
    def __init__(self, receiver_id, content):
        self.receiver_id = receiver_id
        self.content = content