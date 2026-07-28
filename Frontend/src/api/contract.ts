import rawCatalog from './generated/catalog.js';

export interface ContractSchema {
  $ref?: string;
  type?: string;
  format?: string;
  title?: string;
  description?: string;
  enum?: Array<string | number | boolean>;
  nullable?: boolean;
  readOnly?: boolean;
  writeOnly?: boolean;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  minItems?: number;
  maxItems?: number;
  pattern?: string;
  properties?: Record<string, ContractSchema>;
  required?: string[];
  items?: ContractSchema;
  allOf?: ContractSchema[];
  oneOf?: ContractSchema[];
  anyOf?: ContractSchema[];
}

export interface ContractParameter {
  name: string;
  in: 'query' | 'path' | 'header';
  required: boolean;
  description: string;
  schema: ContractSchema;
}

export interface ContractOperation {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  tag: string;
  summary: string;
  description: string;
  parameters: ContractParameter[];
  requestSchema: ContractSchema;
  requestMime: string | null;
  requestRequired: boolean;
  responseSchema: ContractSchema;
  responseMime: string | null;
  statuses: string[];
}

interface Catalog {
  meta: { title: string; version: string; source: string };
  schemas: Record<string, ContractSchema>;
  operations: ContractOperation[];
}

export const contract = rawCatalog as unknown as Catalog;

export function refName(ref: string | undefined): string | null {
  return ref?.split('/').at(-1) ?? null;
}

export function resolveSchema(schema: ContractSchema): ContractSchema {
  if (schema.$ref) {
    const name = refName(schema.$ref);
    return name && contract.schemas[name] ? resolveSchema(contract.schemas[name] as ContractSchema) : schema;
  }
  if (schema.allOf?.length) {
    return schema.allOf.reduce<ContractSchema>((combined, item) => {
      const resolved = resolveSchema(item);
      return {
        ...combined,
        ...resolved,
        properties: { ...(combined.properties ?? {}), ...(resolved.properties ?? {}) },
        required: [...new Set([...(combined.required ?? []), ...(resolved.required ?? [])])],
      };
    }, {});
  }
  return schema;
}

export function operationById(id: string): ContractOperation | undefined {
  return contract.operations.find(operation => operation.id === id);
}

export function operationsForTag(tag: string): ContractOperation[] {
  return contract.operations.filter(operation => operation.tag === tag);
}
