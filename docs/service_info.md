# Service Info

## General
Our team is making a general college management app (with NextJS frontend), and combine of multiple microservice (users, tasks, lms, dispatch, drive,...), with each using a different language.

All other service use user info from the user microservice.
This is the user schema in user serive, we need to follow this.

```json
{
  "sub": 2,
  "user_type": "lecturer", # or student
  "username": "lecturer1",
  "is_admin": false, # only lecturer can be admin
  "email": "lecturer1@system.com",
  "full_name": "Lecturer 1",
  "department_id": 1,
  "class_id": null,
  "iat": 1761899357,
  "exp": 1761902957
}
```

## Addtionally, for dispatch service, the notification service (using Kafka) handle these action from Dispatch Service, to display noti in the frontend
```json
{
    "topic": "official.dispatch",
    "payload": {
        "user_id": 1,
        "user_type": "lecturer",
        "documentTitle": "Thông báo họp khoa định kỳ tháng 9/2025",
        "documentUrl": "https://hpc-system.com/documents/meeting-sep-2025", # the url of the dispatch created
        "documentSerialNumber": "TB-CNTT-092025-001",
        "assignerName": "PGS.TS Trần Văn Minh",
        "assigneeName": "Nguyễn Thị Lan",
        "actionRequired": "Tham dự họp và chuẩn bị báo cáo",
        "date": "2025-09-23 14:30:00",
        "sender_id": 456,
        "sender_type": "lecturer"
    },
    "priority": "medium",
    "key": "official_dispatch_meeting_092025"
}
```

```json
{
    "topic": "official.dispatch.status.update",
    "payload": {
        "user_id": 1,
        "user_type": "lecturer",
        "subject": "Công văn của bạn đã được xử lý",
        "authorName": "Nguyễn Hoài Linh",
        "documentSerialNumber": "123/CV-HPC",
        "documentTitle": "V/v Triển khai kế hoạch năm học 2025-2026",
        "reviewerName": "Nguyễn Ngọc Hiêu",
        "status": "Đã phê duyệt",
        "reviewComment": "Nội dung hợp lệ, đồng ý ban hành.",
        "documentUrl": "https://hpc-app.com/dispatch/clx3x8y7z0000a4b0d1e2f3g4",
        "year": "2025",
        "app_name": "HPC Corp"
    },
    "priority": "medium",
    "key": "official_dispatch_meeting_092025"
}
```

port: `http://localhost:8080/api/v1/events/publish`

## Dispatch Management Service
- Our service is the dispatch microservice, using FastAPI and SQlite.
- *Only* Lecturer or Admin can access dispatch.

### Dispatch Service's Features
- Since our service doesn't create **actual** dispatch, user shall use word or other application to create dispatch, The actual thing we manage in our service is **Dispatch Sending Form**
#### Lecturer
##### Manage **Dispatch Sending Form**
- CRUD Dispatch Sending Form
  -
#### Admin
- Manage all DriveItem of ALL users
