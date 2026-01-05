# Notification Service - Week 2 Updates

## What's New

### 1. RabbitMQ Integration (TASK-9)
- Added RabbitMQ message queue support
- Service can now receive user events from other microservices
- Database polling still works as backup

### 2. Notification API Endpoints (TASK-11)
New REST API endpoints to retrieve and manage notifications:

**GET /api/notifications/{user_email}**
- Get all notifications for a user
- Example: `http://localhost:8001/api/notifications/test@example.com`

**GET /api/notifications/{user_email}/unread**
- Get only unread notifications
- Example: `http://localhost:8001/api/notifications/test@example.com/unread`

**PATCH /api/notifications/{notification_id}**
- Mark notification as read/unread
- Body: `{"is_read": true}`

**GET /health**
- Check service health and dependencies
- Shows database, RabbitMQ, and SMTP status

**GET /api/notifications/stats**
- Get statistics about notifications sent
- Shows total, unread, failed, and success rate

### 3. Notification Storage
- All emails are now saved to the database
- Users can view their notification history
- Track which notifications were read
- Know if email delivery failed

## How to Run

### With Docker (Recommended)
```bash
docker-compose up --build
```

Services will start:
- API: http://localhost:8001/docs
- PostgreSQL: localhost:5433
- RabbitMQ Management UI: http://localhost:15672 (guest/guest)

### Locally (Development)
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## RabbitMQ Message Format

Send messages to `notification_queue` with this JSON format:

**User Created Event:**
```json
{
  "type": "user.created",
  "email": "user@example.com",
  "name": "John Doe"
}
```

**User Deleted Event:**
```json
{
  "type": "user.deleted",
  "email": "user@example.com",
  "name": "John Doe"
}
```

## Testing RabbitMQ

1. Access RabbitMQ Management UI: http://localhost:15672
2. Login with guest/guest
3. Go to Queues tab
4. Click on `notification_queue`
5. Publish a test message using the format above

## Environment Variables

Make sure these are set in `.env.docker`:

```env
# Database
DATABASE_URL=postgresql+psycopg://app:app@db:5432/appdb

# SMTP (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

## TODO for Main Integration (TASK-10)

To integrate with Josh's main docker-compose:

1. Move this service config to main docker-compose.yml
2. Update network to `microservices-network`
3. Change service name to `notification-service`
4. Ensure RabbitMQ is shared across all services
5. Test end-to-end user creation/deletion flow

## Testing the New Features

### Test Notification Storage
1. Create a user via POST /users
2. Check notifications: GET /api/notifications/{email}
3. Mark as read: PATCH /api/notifications/{id}

### Test RabbitMQ
1. Make sure service is running
2. Publish message to notification_queue
3. Check logs for "Received event"
4. Verify email sent and notification saved

### Check Service Health
```bash
curl http://localhost:8001/health
```

Should show all services healthy.
