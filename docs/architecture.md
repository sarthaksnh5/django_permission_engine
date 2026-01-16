# Architecture

## High-Level Architecture

UPR is built on a layered architecture that separates concerns and ensures a clear flow from definition to runtime resolution.

## Conceptual Layers

```
┌──────────────────────────────┐
│ Permission Definition Layer  │  ← Declarative Catalog
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────┐
│ Permission Registry Engine   │  ← Sync / Validation
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────┐
│ Persistence Layer (DB)       │  ← Master Permissions
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────┐
│ Runtime Permission Resolver  │  ← DRF Integration
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────┐
│ Permission Catalog API       │  ← Frontend Consumption
└──────────────────────────────┘
```

## Layer Responsibilities

### 1. Permission Definition Layer

**Purpose**: The single source of truth for all permissions.

**Responsibilities**:
- Declare modules and their structure
- Define CRUD capabilities per module
- Declare custom action permissions
- Provide labels and metadata
- Ensure no permission exists outside this layer

**Characteristics**:
- Declarative (not imperative)
- Code-based (not database-based)
- Version-controlled
- Validated at startup

**Guarantees**:
- No permission exists outside this layer
- No permission is defined twice
- No permission is defined implicitly

### 2. Permission Registry Engine

**Purpose**: Ensures the real system matches the declared system.

**Responsibilities**:
- Register permissions from definitions
- Synchronize database state
- Validate consistency
- Detect breaking changes
- Report orphaned permissions

**Behavior**:
- Runs on:
  - Application startup
  - Deployment
  - Explicit management command (`python manage.py upr_sync`)
- Performs:
  - Create missing permissions
  - Update metadata (labels, descriptions)
  - Detect orphaned permissions
  - Validate permission key format
- Never silently fails

**Output**:
- Synchronized database state
- Validation reports
- Error messages for inconsistencies

### 3. Persistence Layer (Database)

**Purpose**: Persistence is **not authority**, it is **state**.

**Stored Data**:
- Permission key (unique identifier)
- Module name
- Capability name
- Label (human-readable)
- Description (optional)
- Platform/context metadata
- Timestamps (created, updated)

**Rules**:
- No manual editing (except through registry)
- No runtime mutation (except through registry)
- Fully regenerable from definitions
- Immutable permission keys

**Database Models**:
- `Permission` - Core permission storage
- `Module` - Module metadata (optional, for hierarchy)

### 4. Runtime Permission Resolver

**Purpose**: Answer one question efficiently: "Is this user allowed to perform this request?"

**Inputs**:
- Authenticated user
- DRF ViewSet class
- DRF action name
- HTTP method

**Resolution Flow**:
1. Identify module from ViewSet
2. Identify action from DRF context
3. Normalize action (CRUD or custom)
4. Construct permission key (`<module>.<capability>`)
5. Check key presence in user permissions
6. Return allow / deny

**Guarantees**:
- O(1) permission check
- Deterministic results
- No DB joins at runtime (with caching)
- Fast failure (deny by default)

**Integration Points**:
- DRF permission classes
- Django middleware (optional)
- Custom decorators

### 5. Permission Catalog API

**Purpose**: Expose permissions in a **frontend-ready format**.

**Consumers**:
- Admin UI
- Role editors
- Feature toggles
- Auditing tools
- Frontend permission checks

**Characteristics**:
- Read-only
- Declarative
- Hierarchical
- Language-agnostic
- Self-describing

**Response Format**:
```json
{
  "modules": [
    {
      "key": "users",
      "label": "User Management",
      "permissions": [
        {
          "key": "users.view",
          "label": "View Users",
          "capability": "view"
        },
        {
          "key": "users.create",
          "label": "Create Users",
          "capability": "create"
        }
      ]
    }
  ]
}
```

**Guarantees**:
- Matches backend permission logic exactly
- Stable response shape
- Self-describing structure
- No breaking changes without versioning

## Data Flow

### Definition to Runtime

```
Developer defines permissions
    ↓
Registry syncs to database
    ↓
Permissions stored in DB
    ↓
Runtime resolver checks permissions
    ↓
DRF enforces permissions
```

### Runtime Permission Check

```
HTTP Request
    ↓
DRF ViewSet identified
    ↓
Module extracted from ViewSet
    ↓
Action identified (from DRF)
    ↓
Permission key constructed
    ↓
User permissions checked
    ↓
Allow/Deny decision
```

## Component Interactions

### Registry ↔ Database

- **Registry → DB**: Create, update, validate permissions
- **DB → Registry**: Read existing permissions for comparison
- **Conflict Resolution**: Registry always wins (code is source of truth)

### Resolver ↔ Database

- **Resolver → DB**: Read user permissions (cached)
- **DB → Resolver**: Permission existence checks
- **Caching**: Optional caching layer for performance

### Catalog API ↔ Database

- **API → DB**: Read all permissions
- **Formatting**: Transform DB structure to API format
- **Caching**: Response caching for performance

## Extension Points

### Custom Permission Resolvers

The runtime resolver can be extended with custom logic:
- Object-level permissions
- Context-aware permissions
- Time-based permissions

### Custom Registry Hooks

Registry engine supports hooks:
- Pre-sync validation
- Post-sync actions
- Custom validation rules

### Custom Catalog Formats

Catalog API can output multiple formats:
- JSON (default)
- GraphQL
- OpenAPI schema

## Error Handling

### Registry Errors

- **Missing Definitions**: Fail fast, refuse to start
- **Invalid Keys**: Validation errors with clear messages
- **Orphaned Permissions**: Warnings, optional cleanup

### Runtime Errors

- **Missing Permission**: Deny by default
- **Invalid Key Format**: Log error, deny access
- **Database Errors**: Fallback to deny, log error

## Performance Considerations

### Registry Performance

- Batch operations for large permission sets
- Transaction management for consistency
- Minimal database queries

### Runtime Performance

- Permission key caching
- User permission caching
- Minimal database access

### Catalog API Performance

- Response caching
- Pagination for large catalogs
- Selective field loading

## Security Considerations

### Registry Security

- No runtime permission creation
- Validation of all permission keys
- Audit logging of changes

### Runtime Security

- Deny by default
- No permission escalation
- Secure permission key validation

### API Security

- Authentication required
- Rate limiting
- Sensitive data filtering
