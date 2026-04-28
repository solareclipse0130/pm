# Authentication Boundary

The MVP uses a local-only sign-in gate with hardcoded credentials:

```text
username: user
password: password
```

This is not production authentication. The login exists only to hide the board until the user signs in during local MVP testing.

## Current Behavior

- The frontend accepts only `user` and `password`.
- The backend uses the fixed MVP username `user` for board persistence.
- SQLite has a `users` table so future real users can be added later.
- The MVP database does not store passwords.
- API routes are not protected by a real session or token.

## Future Production Work

Before this app is used beyond local MVP testing, replace the hardcoded login with:

- A backend login endpoint.
- Password hashing or an external identity provider.
- A real session or token sent with API requests.
- Backend authorization checks on board and AI endpoints.
- A migration path from the fixed MVP user to real user accounts.
