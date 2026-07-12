# OpenAPI

Generate and validate the schema with:

```bash
make schema
```

The generated contract is committed at `docs/openapi-schema.yml`. CI regenerates it and fails on drift. Swagger UI and ReDoc are served from the running backend. The schema is the frontend contract and must be reviewed for request/response shapes, authentication, permissions, pagination and error examples before an endpoint is declared stable.
