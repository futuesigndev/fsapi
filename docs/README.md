# API Documentation - Authentication & Error Handling

## Quick Start

### Authentication Flow
1. **Client Authentication**: `POST /token` → Get access token
2. **User Authentication**: `POST /api/v1/auth/login` → Get user token  
3. **Use Token**: Include `Authorization: Bearer {token}` header
4. **Handle Expiration**: Check error codes and refresh/re-login

### Token Expiration
- **Expiration Time**: 120 minutes (2 hours)
- **Error Code**: `TOKEN_EXPIRED`, `USER_TOKEN_EXPIRED`, `CLIENT_TOKEN_EXPIRED`
- **Action**: Refresh token or re-authenticate

## Error Code Quick Reference

| Error Code | Meaning | Action |
|------------|---------|--------|
| `TOKEN_EXPIRED` | Token has expired | Refresh or re-login |
| `TOKEN_INVALID` | Malformed token | Re-authenticate |
| `USER_NOT_FOUND` | User account inactive | Contact admin |
| `INVALID_CREDENTIALS` | Wrong client_id/secret | Check credentials |

## Example Implementations

### Frontend (React/JavaScript)
```javascript
// Token refresh utility
const handleApiError = async (response) => {
  if (response.status === 401) {
    const error = await response.json();
    
    if (error.detail.error === 'TOKEN_EXPIRED') {
      // Auto-refresh token
      const newToken = await refreshToken();
      if (newToken) {
        localStorage.setItem('access_token', newToken);
        return 'RETRY_REQUEST';
      }
    }
    
    // Redirect to login for other errors
    window.location.href = '/login';
  }
  return response;
};
```

### Backend (Python)
```python
# API client with auto-retry
class ApiClient:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
    
    def request(self, method, endpoint, **kwargs):
        response = self._make_request(method, endpoint, **kwargs)
        
        if response.status_code == 401:
            error = response.json().get('detail', {})
            if error.get('error') in ['TOKEN_EXPIRED', 'CLIENT_TOKEN_EXPIRED']:
                self._refresh_token()
                response = self._make_request(method, endpoint, **kwargs)
        
        return response
```

## Files for Reference
- 📄 [**Complete Authentication Guide**](./AUTHENTICATION_ERROR_HANDLING.md)
- 📄 [**Error Response Examples**](./TOKEN_ERROR_EXAMPLES.md)

---
*For detailed implementation examples, see the full documentation files above.*
