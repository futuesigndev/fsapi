# FS Central API

## 📖 Overview

FS Central API เป็น API Gateway ที่พัฒนาด้วย FastAPI สำหรับเชื่อมต่อและจัดการการติดต่อกับระบบ SAP และ Oracle Database โดยมีการรองรับระบบ Authentication และ Authorization แบบ JWT Token

## 🎯 Project Concept

### Business Purpose
- **API Gateway**: ทำหน้าที่เป็นตัวกลางในการเชื่อมต่อระหว่างระบบภายนอกกับ SAP และ Oracle
- **Data Integration**: รวมศูนย์การจัดการข้อมูลจากหลายระบบ
- **Security Layer**: ให้ระบบรักษาความปลอดภัยผ่าน JWT Authentication
- **Standardization**: มาตรฐานการเรียกใช้ SAP BAPI Functions
- **Customer Data Services**: ให้บริการข้อมูลลูกค้าแก่ระบบภายนอกผ่าน REST API

### Architecture Concept
```
[External Systems] → [FS Central API] → [SAP System]
                                    → [Oracle Database]
```

## 🏗️ Technical Architecture

### Technology Stack
- **Framework**: FastAPI (Python)
- **SAP Integration**: PyRFC (SAP NetWeaver RFC SDK)
- **Database**: Oracle Database (cx_Oracle)
- **Authentication**: JWT (python-jose)
- **Environment Management**: python-dotenv
- **API Documentation**: OpenAPI (Swagger)

### Project Structure
```
fsapi/
├── app/
│   ├── main.py                 # Application entry point
│   ├── config.py              # Configuration management
│   ├── dependencies.py        # Authentication & authorization
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py        # User authentication endpoints
│   │       ├── sap.py         # SAP integration endpoints
│   │       └── customer.py    # Customer management endpoints
│   ├── schemas/
│   │   ├── token.py           # Token schemas
│   │   ├── user.py            # User schemas
│   │   └── customer.py        # Customer schemas
│   ├── services/
│   │   ├── database_service.py    # Database connection management
│   │   ├── sap_service.py         # SAP connection & operations
│   │   ├── auth_service.py        # Authentication & authorization
│   │   ├── user_service.py        # User management
│   │   └── customer_service.py    # Customer data operations
│   └── sftp-root/
│       └── metadata/          # SAP function metadata files
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## 🔧 Core Components

### 1. SAP Integration Module (`sap.py`)

#### Concept
รับคำขอจาก External Systems และแปลงเป็นการเรียกใช้ SAP BAPI Functions โดยใช้ Metadata-driven approach

#### Technical Details
- **Metadata Validation**: ตรวจสอบความถูกต้องของ Input Parameters ตาม Metadata
- **Dynamic Function Calling**: เรียกใช้ SAP Functions แบบ Dynamic
- **Response Filtering**: กรองข้อมูลตอบกลับตาม Metadata
- **Error Handling**: จัดการ Error และ Return Messages

#### Key Functions
```python
# หลักการทำงาน
load_metadata() → validate_input_parameters() → validate_table_parameters() 
→ prepare_sap_data() → call_bapi() → filter_sap_response()
```

### 2. Authentication System (`auth.py`, `dependencies.py`)

#### Concept
ระบบรักษาความปลอดภัยแบบ 2-Layer:
- **Client Authentication**: สำหรับ External Systems (client_id/client_secret)
- **User Authentication**: สำหรับ End Users (employee_id/password)

#### Technical Implementation
- **JWT Token**: ใช้ JSON Web Token สำหรับ Session Management
- **OAuth2 Bearer**: Standard Bearer Token Authentication
- **Database Integration**: ตรวจสอบ Credentials จาก Oracle Database

### 3. Service Layer Architecture

#### Concept
การแยก Services ตามหน้าที่เฉพาะ (Separation of Concerns) เพื่อง่ายต่อการบำรุงรักษาและขยาย

#### Service Components
- **Database Service**: จัดการการเชื่อมต่อ Oracle Database แบบ Centralized
- **SAP Service**: จัดการการเชื่อมต่อและการทำงานกับ SAP
- **Auth Service**: จัดการการตรวจสอบสิทธิ์ของ Client
- **User Service**: จัดการข้อมูลและการ Authentication ของ User
- **Customer Service**: จัดการข้อมูลลูกค้าและการค้นหา

### 4. SAP Service Layer (`sap_service.py`)

#### Concept
Abstraction Layer สำหรับการเชื่อมต่อและทำงานกับ SAP

#### Technical Features
- **Connection Pooling**: จัดการการเชื่อมต่อ SAP
- **BAPI Calling**: เรียกใช้ SAP Business APIs
- **RFC_READ_TABLE**: อ่านข้อมูลจาก SAP Tables
- **Error Handling**: จัดการ SAP Exceptions

### 5. Metadata System

#### Concept
Configuration-driven approach ที่ใช้ JSON Metadata เพื่อกำหนดโครงสร้างและ Validation Rules

#### Metadata Structure
```json
{
  "function_name": "Z_GET_MATERIALS",
  "description": "DATA MATERIALS MASTER",
  "input_parameters": {
    "I_DATE": {"type": "DATS", "length": 8, "required": true}
  },
  "output_parameters": {
    "RETURN": {...},
    "T_MATERIALS": {...}
  }
}
```

### 6. Customer Management Module (`customer.py`)

#### Concept
ระบบจัดการข้อมูลลูกค้าที่เชื่อมต่อกับ Oracle Database โดยตรง เพื่อให้บริการข้อมูลลูกค้าแก่ระบบภายนอก

#### Technical Features
- **Customer Search**: ค้นหาลูกค้าด้วยเงื่อนไขต่างๆ (หมายเลขลูกค้า, ชื่อ, เมือง)
- **Customer Details**: ดึงข้อมูลรายละเอียดลูกค้าจากหมายเลขลูกค้า
- **Flexible Search**: รองรับการค้นหาแบบ partial match
- **Data Validation**: ตรวจสอบความถูกต้องของข้อมูลผ่าน Pydantic schemas

#### Database Schema
ใช้ข้อมูลจาก Oracle tables:
- **KNA1**: Customer Master (General Data)
- **KNVV**: Customer Master (Sales Data)

#### Search Capabilities
- ค้นหาด้วยหมายเลขลูกค้า (KUNNR)
- ค้นหาด้วยชื่อลูกค้า (NAME1, NAME2)
- ค้นหาด้วยเมือง (ORT01)
- การจำกัดจำนวนผลลัพธ์ (limit)

## 🚀 API Endpoints

### Authentication Endpoints
- `POST /token` - Client authentication (OAuth2)
- `POST /api/v1/auth/login` - User authentication
- `GET /api/v1/users/me` - Get current user information

### SAP Integration Endpoints
- `POST /api/v1/sap/call-function` - Call SAP BAPI functions
- `POST /api/sap/call-function` - Legacy endpoint (deprecated)

### Customer Management Endpoints
- `GET /api/v1/customers/search` - Search customers with query parameters
- `POST /api/v1/customers/search` - Search customers with JSON request body
- `GET /api/v1/customers/{customer_number}` - Get customer details by number

### Health Check
- `GET /` - API health check

## 🔄 Request/Response Flow

### SAP Function Call Flow
```
1. Client Request → JWT Validation
2. Load Function Metadata
3. Validate Input Parameters
4. Validate Table Parameters
5. Prepare SAP Data Format
6. Call SAP BAPI
7. Filter Response Data
8. Return Structured Response
```

### Example Request
```json
{
  "function_name": "Z_GET_MATERIALS",
  "parameters": {
    "input": {
      "I_DATE": "2024.12.31"
    },
    "tables": {
      "T_MATERIALS": {
        "fields": {}
      }
    }
  }
}
```

### Example Response
```json
{
  "status": "success",
  "message": "Execution completed.",
  "sap_response": {
    "RETURN": [...],
    "T_MATERIALS": [...]
  }
}
```

### Customer Search Examples

#### Search by Customer Number (GET)
```bash
GET /api/v1/customers/search?customer_number=1000001&limit=10
```

#### Search by Customer Name (POST)
```json
{
  "customer_name": "ABC Company",
  "limit": 50
}
```

#### Customer Search Response
```json
{
  "status": "success",
  "message": "Found 5 customer(s)",
  "total_records": 5,
  "customers": [
    {
      "KUNNR": "1000001",
      "NAME1": "ABC Company Ltd.",
      "NAME2": "Subsidiary Branch",
      "ORT01": "Bangkok",
      "ORT02": "Chatuchak",
      "STRAS": "123 Main Street",
      "TELF1": "02-555-1234",
      "STCD3": "0105000000123",
      "VTWEG": "10",
      "BZIRK": "001",
      "LPRIO": "02",
      "VKGRP": "001",
      "VKBUR": "001",
      "ZTERM": "N030"
    }
  ]
}
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# SAP Configuration
SAP_USER=your_sap_user
SAP_PASSWORD=your_sap_password
SAP_HOST=your_sap_host
SAP_SYSNR=your_system_number
SAP_CLIENT=your_client
SAP_LANG=EN
SAP_CODEPAGE=1100

# Oracle Configuration  
ORACLE_USER=your_oracle_user
ORACLE_PASSWORD=your_oracle_password
ORACLE_DSN=your_oracle_dsn
ORACLE_CHARSET=UTF8

# Security
SECRET_KEY=your_secret_key_for_jwt
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- SAP NetWeaver RFC SDK
- Oracle Client Libraries
- Access to SAP System
- Access to Oracle Database

### Installation Steps
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fsapi
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   python app/main.py
   ```

## 📊 Monitoring & Logging

### Logging Configuration
- **Log Level**: DEBUG
- **Log Format**: Timestamp - Level - Message
- **Output**: Console + File (app.log)
- **Encoding**: UTF-8

### Monitoring Features
- Request/Response logging
- SAP connection status
- Error tracking
- Performance metrics

## 🔒 Security Features

### Authentication & Authorization
- **JWT Token Expiration**: 120 minutes
- **Client Credential Validation**: Database-driven
- **Employee Authentication**: Oracle integration
- **Token Verification**: Every protected endpoint

### Security Best Practices
- Environment-based configuration
- Password hashing (if implemented)
- Input validation
- Error message sanitization

## 📈 Performance Considerations

### Optimization Features
- **Connection Pooling**: SAP and Oracle connections
- **Async Processing**: FastAPI async endpoints
- **Response Filtering**: Reduce data transfer
- **Metadata Caching**: Reduce file I/O

### Scalability
- **Multi-worker Support**: Uvicorn workers=4
- **Stateless Design**: JWT-based sessions
- **Horizontal Scaling**: Ready for load balancers

## 🧪 Testing & Development

### Development Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### API Documentation
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI Schema**: http://localhost:8001/openapi.json

## 🔧 Troubleshooting

### Common Issues
1. **SAP Connection Errors**: Check SAP credentials and network connectivity
2. **Oracle Connection Errors**: Verify Oracle client installation and DSN
3. **JWT Token Errors**: Check SECRET_KEY configuration
4. **Metadata Not Found**: Verify metadata files in sftp-root/metadata/

### Debug Mode
Enable detailed logging by setting log level to DEBUG in main.py

## 🎓 Development Guidelines

### Code Organization Principles

#### Service Layer Separation
โปรเจกต์นี้ใช้หลักการ **Separation of Concerns** ในการจัดระเบียบโค้ด:

1. **Database Service**: จัดการการเชื่อมต่อฐานข้อมูลแบบ Centralized
   - ใช้ Context Manager สำหรับ Auto-cleanup
   - รองรับ Connection Pooling (อนาคต)

2. **Domain-Specific Services**: แยก Services ตามหน้าที่
   - `auth_service.py`: Client credentials และ SAP function permissions
   - `user_service.py`: Employee authentication และ profile
   - `customer_service.py`: Customer data management
   - `sap_service.py`: SAP integration และ BAPI calls

3. **API Layer**: จัดกลุ่ม endpoints ตาม business domain
   - `auth.py`: User authentication endpoints
   - `sap.py`: SAP integration endpoints  
   - `customer.py`: Customer management endpoints

#### Benefits of This Structure
- **Maintainability**: ง่ายต่อการหาและแก้ไขโค้ด
- **Testability**: สามารถ test แต่ละ service แยกกัน
- **Scalability**: เพิ่ม service ใหม่ได้โดยไม่กระทบ service เดิม
- **Reusability**: service สามารถใช้ร่วมกันได้หลาย endpoint

### Adding New SAP Functions
1. Create metadata JSON file in `sftp-root/metadata/`
2. Define input/output parameters structure
3. Test with SAP system
4. Update documentation

### Code Standards
- **Python Style**: Follow PEP 8
- **Error Handling**: Always use try-catch blocks
- **Logging**: Log important events and errors
- **Documentation**: Document all functions and classes

## 📋 Future Enhancements

### Planned Features
- [ ] Caching layer for frequent requests
- [ ] Request rate limiting
- [ ] Enhanced monitoring dashboard
- [ ] Database connection pooling
- [ ] API versioning strategy
- [ ] Integration tests suite
- [ ] Customer data export functionality
- [ ] Advanced customer search filters
- [ ] Customer analytics and reporting

### Technical Debt
- [ ] Implement proper password hashing
- [ ] Add comprehensive unit tests for each service
- [ ] Optimize metadata loading with caching
- [ ] Implement circuit breaker pattern
- [ ] Add health check endpoints for dependencies
- [ ] Implement connection pooling for Oracle
- [ ] Add service-level logging and monitoring
- [ ] Create abstract base classes for services

---

## 📞 Support

For technical support or questions about this API, please contact the development team.

**API Version**: 1.0.0  
**Last Updated**: December 2024

## 🔄 **Working with Legacy and V1 APIs**

### Current API Structure
โปรเจกต์นี้มี API 2 ชั้น ที่ต้องดูแลอย่างระมัดระวัง:

#### 🔒 **Legacy APIs (ห้ามแตะ!)**
- **`POST /token`** - Client authentication (OAuth2) 
- **`POST /api/sap/call-function`** - SAP integration (เก่า)
- **มี External Apps ใช้งานอยู่** - ถ้าเปลี่ยนจะพังทันที!

#### 🚀 **V1 APIs (ใหม่ - พัฒนาต่อได้)**
- **`POST /api/v1/auth/login`** - User authentication
- **`GET /api/v1/users/me`** - User profile
- **`POST /api/v1/sap/call-function`** - SAP integration (ใหม่)
- **`GET /api/v1/customers/search`** - Customer search
- **`POST /api/v1/customers/search`** - Customer search (POST)
- **`GET /api/v1/customers/{customer_number}`** - Customer details

### 🎯 **Development Guidelines for Adding V1 Features**

#### ✅ **DO's:**
1. **เพิ่มเฉพาะ V1 endpoints ใหม่** ใน `/api/v1/` prefix
2. **ใช้ Services ที่แยกแล้ว** (database_service, customer_service, etc.)
3. **เพิ่ม router ใน main.py** แบบ:
   ```python
   app.include_router(
       new_v1_router.router,
       prefix="/api/v1",
       tags=["New Feature - v1"]
   )
   ```
4. **ทดสอบ V1 ก่อนเสมอ** ก่อนให้ users ใช้งาน

#### ❌ **DON'Ts:**
1. **ห้ามแก้ไข Legacy endpoints** - จะทำ external apps พัง
2. **ห้ามลบ imports เดิม** - อาจมี dependencies ที่ไม่เห็น  
3. **ห้ามเปลี่ยน existing routes** - ต้องเพิ่มใหม่เท่านั้น
4. **ห้ามแก้ไข dependencies.py โดยไม่ระมัดระวัง** - มี legacy auth ใช้อยู่

### 🛠️ **Safe Development Process**

#### When Adding New V1 Features:
1. **เริ่มจาก Service Layer** - สร้าง/แก้ไข services ก่อน
2. **สร้าง Schemas** - กำหนด request/response models  
3. **สร้าง API Router** - ใน `/app/api/v1/` folder
4. **เพิ่ม Router ใน main.py** - ใช้ `/api/v1` prefix
5. **ทดสอบทีละขั้นตอน** - ตรวจสอบไม่กระทบของเดิม

#### Directory Structure for V1:
```
app/
├── api/v1/           # V1 API endpoints (safe to modify)
├── services/         # Shared services (modify carefully)  
├── schemas/          # Pydantic models (safe to add)
└── main.py          # Add V1 routers here only
```

### 🚨 **Critical Warnings**

#### For AI Assistant (GitHub Copilot):
- **NEVER modify existing Legacy endpoints**
- **ALWAYS use `/api/v1` prefix for new features**
- **ALWAYS ask before changing shared services**
- **ALWAYS preserve existing functionality**

#### For Developers:
- **Backup before making changes**
- **Test Legacy endpoints after any modification**
- **Document all new V1 features**
- **Keep V1 and Legacy clearly separated**

## 🛠️ Core Components

### Customer Management Modernization (V1)

- **Standardized Error Responses**: All customer endpoints now return errors in a consistent format using the `StandardError` schema. Error responses include fields: `error`, `code`, `message`, `details`, `timestamp`, and `request_id`.
- **In-Memory Caching**: The `/customers/lookup` endpoint uses a 30-second in-memory cache to reduce backend/SAP load for repeated queries.
- **Robust Search/Lookup**:
  - **Partial Search**: Lookup by name, phone, or tax ID supports partial matches (SQL `LIKE`).
  - **Phone Search Normalization**: Phone search strips all non-digits from both input and database (using `REGEXP_REPLACE` in Oracle), so users can search without worrying about dashes or spaces.
  - **Phone Search Logic**: Only matches phone numbers starting with the search string (e.g., searching `092248` matches numbers starting with `092248`, not those containing it elsewhere).
- **Code Refactoring**: Service logic is modularized in `customer_service.py` for maintainability.
- **Unused Files Removed**: `sap_clean.py` is now removed as it was unused.

#### Example Error Response
```json
{
  "error": "CustomerNotFound",
  "code": 404,
  "message": "Customer 123456 not found",
  "details": null,
  "timestamp": "2025-07-02T09:33:38.081993",
  "request_id": "e4356e12-b451-4e07-8198-5b221bd7b474"
}
```

#### Example Lookup Request
```
GET /api/v1/customers/lookup?phone=092248
```
- Matches all phone numbers starting with `092248`, ignoring formatting.

---

## คู่มือการใช้งาน API: `POST /api/v1/sap/call-function`

#### 1. Endpoint
```
POST /api/v1/sap/call-function
Content-Type: application/json
Authorization: Bearer <JWT Token>
```

#### 2. Request Body Structure
```json
{
  "function_name": "<SAP_FUNCTION_NAME>",
  "parameters": {
    "input": {
      "<PARAM1>": "<value>",
      "<PARAM2>": "<value>"
    },
    "tables": {
      "<TABLE_NAME>": {
        "fields": {
          "<FIELD1>": "<value>",
          "<FIELD2>": "<value>"
        }
      }
    }
  }
}
```
- `function_name`: ชื่อ SAP BAPI หรือ Z Function ที่ต้องการเรียก เช่น `Z_GET_MATERIALS`
- `parameters.input`: (optional) พารามิเตอร์ input (single value)
- `parameters.tables`: (optional) พารามิเตอร์แบบ table (array หรือ dict)

#### 3. ตัวอย่าง Request (Input + Table)
```json
{
  "function_name": "Z_GET_MATERIALS_NEW",
  "parameters": {
    "input": {
      "I_DATE": "2025.07.02"
    },
    "tables": {
      "T_MATERIALS": {
        "fields": {
          "MATNR": "1000001"
        }
      }
    }
  }
}
```

#### 4. ตัวอย่าง Request (Input Only)
```json
{
  "function_name": "Z_GET_MATERIALS",
  "parameters": {
    "input": {
      "I_DATE": "2025.07.02"
    }
  }
}
```

#### 5. ตัวอย่าง Request (Table Only)
```json
{
  "function_name": "ZMAST_CUSTOMER",
  "parameters": {
    "tables": {
      "T_CUSTOMERS": {
        "fields": {
          "KUNNR": "1000001"
        }
      }
    }
  }
}
```

#### 6. ตัวอย่าง Response (Success)
```json
{
  "status": "success",
  "message": "Execution completed.",
  "sap_response": {
    "RETURN": [
      {"TYPE": "S", "MESSAGE": "Success"}
    ],
    "T_MATERIALS": [
      {"MATNR": "1000001", "MAKTX": "Product A"},
      {"MATNR": "1000002", "MAKTX": "Product B"}
    ]
  }
}
```

#### 7. ตัวอย่าง Response (Error)
```json
{
  "status": "error",
  "message": "Function not found: Z_FAKE_FUNCTION",
  "sap_response": null
}
```

#### 8. ข้อควรระวังและแนวทางการใช้งาน
- ต้องระบุ `function_name` ให้ตรงกับ metadata ที่มีในระบบ (ดูไฟล์ใน `app/sftp-root/metadata/`)
- ชื่อ field/payload ต้องตรงกับ metadata (case-sensitive)
- ถ้า parameter ไม่ถูกต้อง ระบบจะ return error พร้อมรายละเอียด
- ต้องแนบ JWT Token ใน header ทุกครั้ง
- สามารถดูรายละเอียด input/output ของแต่ละ function ได้จาก metadata JSON

#### 9. การตรวจสอบ metadata
- สามารถขอดูตัวอย่าง metadata ได้ที่ไฟล์ `app/sftp-root/metadata/<function_name>.json`
- ตัวอย่าง metadata:
```json
{
  "function_name": "Z_GET_MATERIALS",
  "description": "DATA MATERIALS MASTER",
  "input_parameters": {
    "I_DATE": {"type": "DATS", "length": 8, "required": true}
  },
  "output_parameters": {
    "RETURN": {...},
    "T_MATERIALS": {...}
  }
}
```

#### 10. Troubleshooting
- ถ้า response เป็น error ให้ตรวจสอบชื่อ function, โครงสร้าง input, และ JWT Token
- ดูรายละเอียด error message ใน response เพื่อแก้ไข

---
