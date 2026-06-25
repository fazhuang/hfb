# API Design Template: [Resource Name]

**Version**: v1
**Date**: YYYY-MM-DD
**Author**: [Name]
**Status**: draft | review | approved

---

## Overview

Brief description of what this API resource provides.

## Endpoints

### `GET /api/v1/[resource]`

**Description**: List all [resource] items.

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number |
| `limit` | integer | No | 20 | Items per page (max 100) |
| `q` | string | No | — | Search query |
| `sort` | string | No | `-created_at` | Sort field (prefix with `-` for desc) |

**Response**:
```json
{
  "data": [],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 0,
    "total_pages": 0
  }
}
```

**Status Codes**: `200`, `400`, `401`, `500`

---

### `POST /api/v1/[resource]`

**Description**: Create a new [resource].

**Request Body**:
```json
{
  "name": "string (required)",
  "description": "string (optional)"
}
```

**Response**: `201 Created`
```json
{
  "data": {},
  "meta": {}
}
```

**Validation Rules**: [Describe validation logic]

---

### `GET /api/v1/[resource]/{id}`

**Description**: Get a specific [resource] by ID.

**Response**: `200 OK`
```json
{
  "data": {},
  "meta": {}
}
```

**Status Codes**: `200`, `404`, `500`

---

### `PUT /api/v1/[resource]/{id}`

**Description**: Update an existing [resource].

**Request Body**: Same as POST, all fields optional.

**Response**: `200 OK`

---

### `DELETE /api/v1/[resource]/{id}`

**Description**: Soft-delete a [resource].

**Response**: `204 No Content`

---

## Data Model

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK | Primary key |
| `name` | string | required, max 255 | Display name |
| `created_at` | datetime | auto | Creation timestamp |
| `updated_at` | datetime | auto | Last update timestamp |

## Permissions

| Action | Role |
|--------|------|
| `read` | public, user, admin |
| `create` | user, admin |
| `update` | owner, admin |
| `delete` | admin |

## Notes

- [Any additional implementation notes]
