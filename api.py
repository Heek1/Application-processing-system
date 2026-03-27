from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from model import *
from db import users, requests_db, comments, messages
from bson import ObjectId
from typing import Optional
from datetime import datetime

app = FastAPI(title="Application Processing System API")

def convert_objectid(doc):
    if doc is None:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

@app.get("/")
def home():
    return {"message": "Application Processing System is working"}


@app.post("/user/add")
async def add_user(request: Request):
    try:
        user_data = await request.json()
        tg_id = user_data.get("tg_id")
        full_name = user_data.get("full_name")
        role = user_data.get("role", "client").lower()

        if not tg_id or not full_name:
            raise HTTPException(status_code=400, detail="tg_id and full_name are required")

        existing_user = users.find_one({"tg_id": tg_id})
        if existing_user:
            return JSONResponse(
                status_code=400,
                content={"message": "User already exists", "user": convert_objectid(existing_user)}
            )

        if role == "admin":
            user_obj = Admin(tg_id, full_name)
        elif role == "manager":
            user_obj = Manager(tg_id, full_name)
        else:
            user_obj = Client(tg_id, full_name)

        user_dict = user_obj.to_dict()
        user_dict["created_at"] = datetime.now()

        result = users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)

        return user_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{tg_id}")
def get_user(tg_id: int):
    try:
        user = users.find_one({"tg_id": tg_id})
        if not user:
            raise HTTPException(status_code=404, detail="User doesn't exist")
        return convert_objectid(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users")
def get_all_users(role: Optional[str] = None):
    try:
        query = {}
        if role:
            query["role"] = role
        users_list = list(users.find(query))
        return [convert_objectid(user) for user in users_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/user/{tg_id}/role")
async def update_user_role(tg_id: int, request: Request):
    try:
        data = await request.json()
        new_role = data.get("role")

        if new_role not in ["client", "manager", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")

        result = users.update_one(
            {"tg_id": tg_id},
            {"$set": {"role": new_role}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User doesn't exist")

        user = users.find_one({"tg_id": tg_id})
        return convert_objectid(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/request/add")
async def add_request(request: Request):
    try:
        data = await request.json()
        client_id = data.get("client_id")
        text = data.get("text")

        if not client_id or not text:
            raise HTTPException(status_code=400, detail="client_id and text are required")

        client = users.find_one({"tg_id": client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client doesn't exist")

        last_request = requests_db.find_one(sort=[("request_id", -1)])
        new_request_id = (last_request["request_id"] + 1) if last_request else 1

        request_obj = RequestModel(new_request_id, client_id, text)
        request_dict = request_obj.to_dict()
        request_dict["created_at"] = datetime.now()
        request_dict["updated_at"] = datetime.now()

        result = requests_db.insert_one(request_dict)
        request_dict["_id"] = str(result.inserted_id)

        return request_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/request/{request_id}")
def get_request(request_id: int):
    try:
        request_data = requests_db.find_one({"request_id": request_id})
        if not request_data:
            raise HTTPException(status_code=404, detail="Request doesn't exist")
        return convert_objectid(request_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{tg_id}/requests")
def get_user_requests(tg_id: int, status: Optional[str] = None):
    try:
        query = {"client_id": tg_id}
        if status:
            query["status"] = status

        requests_list = list(requests_db.find(query).sort("created_at", -1))
        return [convert_objectid(req) for req in requests_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/requests")
def get_all_requests(status: Optional[str] = None):
    try:
        query = {}
        if status:
            query["status"] = status

        requests_list = list(requests_db.find(query).sort("created_at", -1))
        return [convert_objectid(req) for req in requests_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/request/{request_id}/status")
async def update_request_status(request_id: int, request: Request):
    try:
        data = await request.json()
        new_status = data.get("status")
        manager_id = data.get("manager_id")

        valid_statuses = ["Нова", "В обробці", "Виконано", "Відхилено"]
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

        if not manager_id:
            raise HTTPException(status_code=400, detail="manager_id is required")

        manager = users.find_one({"tg_id": manager_id, "role": {"$in": ["manager", "admin"]}})
        if not manager:
            raise HTTPException(status_code=403, detail="Only managers or admins can change status")

        result = requests_db.update_one(
            {"request_id": request_id},
            {"$set": {"status": new_status, "updated_at": datetime.now()}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Request doesn't exist")

        request_data = requests_db.find_one({"request_id": request_id})
        if request_data:
            msg_content = f"Статус вашої заявки #{request_id} змінено на: {new_status}"
            add_notification(request_data["client_id"], msg_content)

        request_data = requests_db.find_one({"request_id": request_id})
        return convert_objectid(request_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comment/add")
async def add_comment(request: Request):
    try:
        data = await request.json()
        request_id = data.get("request_id")
        user_id_tg = data.get("user_id_tg")
        text = data.get("text")

        if not request_id or not user_id_tg or not text:
            raise HTTPException(status_code=400, detail="request_id, user_id_tg and text are required")

        request_data = requests_db.find_one({"request_id": request_id})
        if not request_data:
            raise HTTPException(status_code=404, detail="Request doesn't exist")

        user = users.find_one({"tg_id": user_id_tg})
        if not user:
            raise HTTPException(status_code=404, detail="User doesn't exist")

        last_comment = comments.find_one(sort=[("com_id", -1)])
        new_comment_id = (last_comment["com_id"] + 1) if last_comment else 1

        comment_obj = Comment(request_id, user_id_tg, text, new_comment_id)
        comment_dict = comment_obj.to_dict()
        comment_dict["created_at"] = datetime.now()

        result = comments.insert_one(comment_dict)
        comment_dict["_id"] = str(result.inserted_id)

        requests_db.update_one(
            {"request_id": request_id},
            {"$push": {"comments": comment_dict}}
        )

        return comment_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/request/{request_id}/comments")
def get_request_comments(request_id: int):
    try:
        comments_list = list(comments.find({"req_id": request_id}).sort("created_at", 1))
        return [convert_objectid(comment) for comment in comments_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/message/send")
async def send_message(request: Request):
    try:
        data = await request.json()
        receiver_id = data.get("receiver_id")
        content = data.get("content")
        sender_id = data.get("sender_id")

        if not receiver_id or not content:
            raise HTTPException(status_code=400, detail="receiver_id and content are required")

        receiver = users.find_one({"tg_id": receiver_id})
        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver doesn't exist")

        last_msg = messages.find_one(sort=[("msg_id", -1)])
        new_msg_id = (last_msg["msg_id"] + 1) if last_msg else 1

        msg_obj = Msg(new_msg_id, receiver_id, content)
        msg_dict = msg_obj.to_dict()
        msg_dict["sender_id"] = sender_id
        msg_dict["created_at"] = datetime.now()
        msg_dict["is_read"] = False

        result = messages.insert_one(msg_dict)
        msg_dict["_id"] = str(result.inserted_id)

        return msg_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{tg_id}/messages")
def get_user_messages(tg_id: int, unread_only: bool = False):
    try:
        query = {"receiver_id": tg_id}
        if unread_only:
            query["is_read"] = False

        messages_list = list(messages.find(query).sort("created_at", -1))
        return [convert_objectid(msg) for msg in messages_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/message/{msg_id}/read")
async def mark_message_read(msg_id: int):
    try:
        result = messages.update_one(
            {"msg_id": msg_id},
            {"$set": {"is_read": True}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Message doesn't exist")

        return {"message": "Message marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def add_notification(user_id, content):
    try:
        last_msg = messages.find_one(sort=[("msg_id", -1)])
        new_msg_id = (last_msg["msg_id"] + 1) if last_msg else 1

        msg_obj = Msg(new_msg_id, user_id, content)
        msg_dict = msg_obj.to_dict()
        msg_dict["created_at"] = datetime.now()
        msg_dict["is_read"] = False
        msg_dict["is_notification"] = True

        messages.insert_one(msg_dict)
    except Exception:
        pass

@app.get("/stats")
def get_stats():
    try:
        total_users = users.count_documents({})
        total_requests = requests_db.count_documents({})
        total_comments = comments.count_documents({})

        requests_by_status = []
        for status in ["Нова", "В обробці", "Виконано", "Відхилено"]:
            count = requests_db.count_documents({"status": status})
            requests_by_status.append({"status": status, "count": count})

        users_by_role = []
        for role in ["client", "manager", "admin"]:
            count = users.count_documents({"role": role})
            users_by_role.append({"role": role, "count": count})

        return {
            "total_users": total_users,
            "total_requests": total_requests,
            "total_comments": total_comments,
            "requests_by_status": requests_by_status,
            "users_by_role": users_by_role
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )