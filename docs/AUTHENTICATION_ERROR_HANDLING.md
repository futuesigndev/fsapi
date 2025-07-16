# Authentication & Token Error Handling Guide

## Overview
This document describes how to handle authentication errors and token expiration in the FS Central API system.

## Token Types

### 1. Client Token (Legacy)
- **Endpoint**: `POST /token`
- **Usage**: Legacy API authentication
- **Expiration**: 120 minutes (2 hours)
- **Type**: `client` (default)

### 2. User Token (V1)
- **Endpoint**: `POST /api/v1/auth/login`
- **Usage**: V1 API user authentication
- **Expiration**: 120 minutes (2 hours)
- **Type**: `user`

## Error Response Format

All authentication errors return `HTTP 401 Unauthorized` with detailed error information:

```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Human readable message",
    "timestamp": "2025-07-04T10:30:00.000000",
    "type": "authentication_error",
    "action": "suggested_action"
  }
}
```

## Error Codes & Handling

### Client Token Errors

| Error Code | Description | Action Required |
|------------|-------------|-----------------|
| `CLIENT_TOKEN_EXPIRED` | Client token has expired | Request new token via `/token` |
| `CLIENT_TOKEN_INVALID` | Invalid client token format | Request new token via `/token` |
| `CLIENT_TOKEN_ERROR` | General client token error | Request new token via `/token` |
| `INVALID_CLIENT_TOKEN` | Invalid token structure | Check token format and request new token |

### User Token Errors

| Error Code | Description | Action Required |
|------------|-------------|-----------------|
| `USER_TOKEN_EXPIRED` | User token has expired | Re-login via `/api/v1/auth/login` |
| `USER_TOKEN_INVALID` | Invalid user token format | Re-login via `/api/v1/auth/login` |
| `USER_TOKEN_ERROR` | General user token error | Re-login via `/api/v1/auth/login` |
| `INVALID_USER_TOKEN` | Invalid token structure | Re-login via `/api/v1/auth/login` |
| `USER_NOT_FOUND` | User account not found/inactive | Contact administrator |

### General Token Errors

| Error Code | Description | Action Required |
|------------|-------------|-----------------|
| `TOKEN_EXPIRED` | Any token has expired | Refresh token or re-login |
| `TOKEN_INVALID` | Invalid token format | Refresh token or re-login |
| `TOKEN_ERROR` | General token error | Refresh token or re-login |
| `INVALID_TOKEN_STRUCTURE` | Malformed token | Check token format |

## Implementation Examples

### Frontend JavaScript Error Handling

```javascript
async function apiCall(endpoint, data) {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (response.status === 401) {
      const errorData = await response.json();
      
      switch (errorData.detail.error) {
        case 'CLIENT_TOKEN_EXPIRED':
        case 'CLIENT_TOKEN_INVALID':
          // Refresh client token
          await refreshClientToken();
          break;
          
        case 'USER_TOKEN_EXPIRED':
        case 'USER_TOKEN_INVALID':
          // Redirect to login
          window.location.href = '/login';
          break;
          
        case 'USER_NOT_FOUND':
          // Show admin contact message
          showErrorMessage('Account inactive. Contact administrator.');
          break;
          
        default:
          // General error handling
          showErrorMessage(errorData.detail.message);
      }
      
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error('API call failed:', error);
    return null;
  }
}
```

### Python Client Error Handling

```python
import requests
import json

def handle_api_response(response):
    """Handle API response and authentication errors"""
    
    if response.status_code == 401:
        error_data = response.json()
        error_detail = error_data.get('detail', {})
        error_code = error_detail.get('error', '')
        
        if error_code in ['CLIENT_TOKEN_EXPIRED', 'CLIENT_TOKEN_INVALID']:
            # Refresh client token
            refresh_client_token()
            return 'TOKEN_REFRESHED'
            
        elif error_code in ['USER_TOKEN_EXPIRED', 'USER_TOKEN_INVALID']:
            # Re-login required
            print(f"Login required: {error_detail.get('message')}")
            return 'LOGIN_REQUIRED'
            
        elif error_code == 'USER_NOT_FOUND':
            # Account issue
            print(f"Account error: {error_detail.get('message')}")
            return 'ACCOUNT_ERROR'
            
        else:
            print(f"Authentication error: {error_detail.get('message')}")
            return 'AUTH_ERROR'
    
    return response

# Usage example
response = requests.post(
    'http://localhost:8001/api/v1/billing/create',
    headers={'Authorization': f'Bearer {access_token}'},
    json={'delivery_number': '8000123456', 'test_run': True}
)

result = handle_api_response(response)
if result == 'TOKEN_REFRESHED':
    # Retry the request with new token
    pass
elif result == 'LOGIN_REQUIRED':
    # Redirect to login
    pass
```

### Postman/API Testing

```javascript
// Postman Pre-request Script
if (pm.response.code === 401) {
    const responseJson = pm.response.json();
    const errorCode = responseJson.detail.error;
    
    if (errorCode === 'CLIENT_TOKEN_EXPIRED') {
        // Auto-refresh client token
        pm.sendRequest({
            url: pm.environment.get('base_url') + '/token',
            method: 'POST',
            header: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: {
                mode: 'urlencoded',
                urlencoded: [
                    {key: 'client_id', value: pm.environment.get('client_id')},
                    {key: 'client_secret', value: pm.environment.get('client_secret')}
                ]
            }
        }, function (err, response) {
            if (!err && response.code === 200) {
                const newToken = response.json().access_token;
                pm.environment.set('access_token', newToken);
                console.log('Token refreshed automatically');
            }
        });
    }
}
```

## Best Practices

### For API Consumers

1. **Always check error codes** - Don't rely only on HTTP status codes
2. **Implement token refresh logic** - Automatically handle expired tokens
3. **Store error details** - Log error codes and timestamps for debugging
4. **Graceful degradation** - Show appropriate user messages
5. **Retry mechanism** - Implement smart retry for token refresh scenarios

### For API Developers

1. **Consistent error format** - Always use the standardized error structure
2. **Specific error codes** - Provide actionable error codes
3. **Helpful messages** - Include clear, user-friendly messages
4. **Timestamp everything** - Include timestamps for debugging
5. **Log appropriately** - Log errors without exposing sensitive data

## Security Considerations

1. **Token Storage** - Store tokens securely (httpOnly cookies recommended)
2. **Token Transmission** - Always use HTTPS in production
3. **Token Rotation** - Implement token refresh mechanisms
4. **Error Information** - Don't expose sensitive details in error messages
5. **Rate Limiting** - Implement rate limiting for authentication endpoints

## Testing Error Scenarios

### Manual Testing

1. **Expired Token**: Wait for token expiration or manually set expired timestamp
2. **Invalid Token**: Use malformed or incorrect tokens
3. **User Deactivation**: Test with deactivated user accounts
4. **Network Issues**: Test offline/timeout scenarios

### Automated Testing

```python
# Example test cases
def test_expired_token():
    # Test with expired token
    expired_token = create_expired_token()
    response = api_call_with_token(expired_token)
    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'TOKEN_EXPIRED'

def test_invalid_token():
    # Test with invalid token
    invalid_token = "invalid.token.here"
    response = api_call_with_token(invalid_token)
    assert response.status_code == 401
    assert response.json()['detail']['error'] == 'TOKEN_INVALID'
```

## Monitoring & Alerting

### Key Metrics to Monitor

1. **Token expiration rate** - How often tokens expire
2. **Authentication failure rate** - Failed authentication attempts
3. **Error code distribution** - Which errors occur most frequently
4. **Token refresh frequency** - How often tokens are refreshed

### Alert Thresholds

- High authentication failure rate (>5% in 5 minutes)
- Unusual error code patterns
- Token expiration spikes
- User account lockouts

---

**Last Updated**: July 4, 2025  
**Version**: 1.0  
**Contact**: FS Central API Team
