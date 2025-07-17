# FSAPI Authentication API Documentation

## Overview
This document describes the usage of authentication-related endpoints for the FSAPI service. These endpoints provide JWT-based authentication and user profile retrieval for client applications.

---

## 1. `/token` (Client Credentials Token)

**Method:** `POST`

**Description:**
- Obtain an access token using client credentials (for system-to-system authentication).

**Request Body (application/x-www-form-urlencoded):**
```
grant_type=client_credentials
client_id=YOUR_CLIENT_ID
client_secret=YOUR_CLIENT_SECRET
```

**Response:**
```
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer",
  "expires_in": 7200
}
```

**Usage:**
- Use the returned `access_token` as a Bearer token in the `Authorization` header for subsequent API calls.

---

## 2. `/api/v1/auth/login` (User Login)

**Method:** `POST`

**Description:**
- Authenticate a user (employee) and receive a JWT access token for user-level access.

**Request Body (application/json):**
```
{
  "employee_id": "EMPLOYEE_ID",
  "password": "LAST4DIGITS_OF_EMPLOYEE_CARD"
}
```

**Response:**
```
{
  "status": "success",
  "message": "Login successful",
  "user_data": {
    "employee_id": "...",
    "employee_name": "...",
    "employee_card": "...",
    "access_token": "<JWT_TOKEN>",
    "token_type": "bearer"
  }
}
```

**Usage:**
- Use the `access_token` from `user_data` as a Bearer token in the `Authorization` header for user-specific API calls.

---

## 3. `/api/v1/auth/me` (Get Current User Profile)

**Method:** `GET`

**Description:**
- Retrieve the profile of the currently authenticated user (based on the JWT token).

**Headers:**
```
Authorization: Bearer <USER_ACCESS_TOKEN>
```

**Response:**
```
{
  "employee_id": "...",
  "employee_name": "...",
  "department": "...",
  "employee_card": "...",
  "division_desc_th": "...",
  "department_name_th": "...",
  "section_name": "...",
  "nationality": "..."
}
```

**Usage:**
- Use this endpoint to get the current user's profile information after login.

---

## Notes
- All endpoints return errors in standard JSON format with `status_code` and `detail` fields.
- Always use HTTPS in production.
- JWT tokens are required for all protected endpoints.

---

For further details or troubleshooting, contact the API development team.
