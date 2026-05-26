import api from "../lib/api";
import type {
  DatabaseMetadataNodeRequest,
  DatabaseMetadataNodeResponse,
  OpenDatabaseMetadataRequest,
  OpenDatabaseMetadataResponse,
} from "../types/databaseMetadata";

export async function openDatabaseMetadata(
  data: OpenDatabaseMetadataRequest,
): Promise<OpenDatabaseMetadataResponse> {
  const response = await api.post("/database-metadata/open", data);
  return response.data as OpenDatabaseMetadataResponse;
}

export async function loadDatabaseMetadataNode(
  data: DatabaseMetadataNodeRequest,
): Promise<DatabaseMetadataNodeResponse> {
  const response = await api.post("/database-metadata/load-node", data);
  return response.data as DatabaseMetadataNodeResponse;
}

export async function refreshDatabaseMetadataNode(
  data: DatabaseMetadataNodeRequest,
): Promise<DatabaseMetadataNodeResponse> {
  const response = await api.post("/database-metadata/refresh-node", data);
  return response.data as DatabaseMetadataNodeResponse;
}
