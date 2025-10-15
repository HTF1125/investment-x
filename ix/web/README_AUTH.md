# Authentication System

This application now includes a complete authentication system with login, registration, and protected routes.

## Features

- **User Registration**: New users can create accounts with username, email, and password
- **Secure Login**: Uses bcrypt for password hashing and JWT for session management
- **Protected Routes**: All routes except `/login` and `/register` require authentication
- **Session Management**: JWT tokens stored in browser session storage
- **User Menu**: Displays logged-in user info with profile, settings, and logout options

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Admin User

Before you can log in, create an admin user:

```bash
python create_admin.py
```

Or with command line arguments:

```bash
python create_admin.py admin password123 admin@example.com
```

### 3. Run the Application

```bash
python -m ix.web.app
```

### 4. Access the Login Page

Navigate to: `http://localhost:8050/login`

## Security Features

- **Password Hashing**: Uses bcrypt with salt for secure password storage
- **JWT Tokens**: Secure token-based authentication
- **Session Storage**: Tokens stored in browser session (cleared on browser close)
- **Token Expiration**: Tokens expire after 24 hours
- **Password Requirements**: Minimum 6 characters for passwords
- **Username Requirements**: Minimum 3 characters for usernames

## API Endpoints

### Authentication

- `POST /login` - User login
- `POST /register` - New user registration
- `POST /logout` - User logout

## User Roles

- **Regular User**: Can access all protected routes
- **Admin**: Has additional privileges (future feature)

## Environment Variables

For production, set the following environment variables:

```bash
SECRET_KEY=your-secret-key-here  # JWT signing key
```

⚠️ **Important**: Change the SECRET_KEY in `ix/misc/auth.py` for production use!

## Troubleshooting

### Cannot Login

1. Check that the user exists in the database
2. Verify the password is correct
3. Check browser console for errors
4. Ensure MongoDB is running

### Token Expired

- Tokens expire after 24 hours
- Simply log in again to get a new token

### Database Connection Issues

- Ensure MongoDB is running
- Check connection settings in `ix/db/conn.py`

## Development

### Creating Additional Users

You can create users programmatically:

```python
from ix.db.models import User

# Create regular user
User.new_user(username="john", password="password123", email="john@example.com")

# Create admin user
User.new_user(username="admin2", password="password123", is_admin=True)
```

### Checking Authentication Status

In callbacks, you can access the current user:

```python
from ix.misc.auth import get_current_user

@callback(...)
def my_callback(token_data):
    if token_data:
        user = get_current_user(token_data["token"])
        if user:
            # User is authenticated
            pass
```

## Security Best Practices

1. **Change Secret Key**: Update SECRET_KEY in production
2. **Use HTTPS**: Always use HTTPS in production
3. **Regular Updates**: Keep dependencies up to date
4. **Strong Passwords**: Enforce strong password policies
5. **Monitor Logs**: Check logs for suspicious activity

## Future Enhancements

- [ ] Password reset functionality
- [ ] Email verification
- [ ] Two-factor authentication
- [ ] Remember me option
- [ ] Session timeout warning
- [ ] Admin dashboard for user management
- [ ] Role-based access control (RBAC)
- [ ] OAuth integration (Google, GitHub, etc.)
