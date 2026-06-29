import api from "../lib/api";
import type {
  DatabaseMetadataNodeRequest,
  DatabaseMetadataNodeResponse,
  OpenDatabaseMetadataRequest,
  OpenDatabaseMetadataResponse,
  ProcedureDdlRequest,
  ProcedureDdlResponse,
  SourceDdlRequest,
  SourceDdlResponse,
  TableDdlRequest,
  TableDdlResponse,
} from "../types/databaseMetadata";

export async function openDatabaseMetadata(
  data: OpenDatabaseMetadataRequest,
): Promise<OpenDatabaseMetadataResponse> {
  const response = await api.post("/database-metadata/open", data, {
    timeout: 180000,
  });
  return response.data as OpenDatabaseMetadataResponse;
}

export async function loadDatabaseMetadataNode(
  data: DatabaseMetadataNodeRequest,
): Promise<DatabaseMetadataNodeResponse> {
  const response = await api.post("/database-metadata/load-node", data, {
    timeout: 180000,
  });
  return response.data as DatabaseMetadataNodeResponse;
}

export async function refreshDatabaseMetadataNode(
  data: DatabaseMetadataNodeRequest,
): Promise<DatabaseMetadataNodeResponse> {
  const response = await api.post("/database-metadata/refresh-node", data, {
    timeout: 180000,
  });
  return response.data as DatabaseMetadataNodeResponse;
}

export async function fetchTableDdl(
  data: TableDdlRequest,
): Promise<TableDdlResponse> {
  const response = await api.post("/database-metadata/table-ddl", data, {
    timeout: 180000,
  });
  return response.data as TableDdlResponse;
}

export async function fetchProcedureDdl(
  data: ProcedureDdlRequest,
): Promise<ProcedureDdlResponse> {
  const response = await api.post("/database-metadata/procedure-ddl", data, {
    timeout: 180000,
  });
  return response.data as ProcedureDdlResponse;
}

export async function fetchSourceDdl(
  data: SourceDdlRequest,
): Promise<SourceDdlResponse> {
  const response = await api.post("/database-metadata/source-ddl", data, {
    timeout: 180000,
  });
  return response.data as SourceDdlResponse;
}
