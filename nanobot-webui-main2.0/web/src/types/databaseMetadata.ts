export interface MetadataTreeNode {
  id: string;
  label: string;
  type: string;
  icon?: string;
  loaded?: boolean;
  children?: MetadataTreeNode[];
  metadata?: Record<string, unknown>;
}

export interface OpenDatabaseMetadataRequest {
  connectionId: string;
  sqlclConnectionName: string;
  displayName: string;
}

export interface OpenDatabaseMetadataResponse {
  success: boolean;
  fromCache: boolean;
  connectionId: string;
  tree: MetadataTreeNode;
}

export interface DatabaseMetadataNodeRequest {
  connectionId: string;
  sqlclConnectionName: string;
  nodeId: string;
  nodeType: string;
  schemaName?: string;
}

export interface DatabaseMetadataNodeResponse {
  success: boolean;
  fromCache: boolean;
  connectionId: string;
  node: MetadataTreeNode;
}

export interface TableDdlRequest {
  connectionId: string;
  sqlclConnectionName: string;
  schemaName: string;
  tableName: string;
  forceRefresh?: boolean;
}

export interface TableDdlResponse {
  success: boolean;
  connectionId: string;
  sqlText: string;
  cachePath: string;
  cacheHit: boolean;
}

export interface ProcedureDdlRequest {
  connectionId: string;
  sqlclConnectionName: string;
  schemaName: string;
  procedureName: string;
  forceRefresh?: boolean;
}

export interface ProcedureDdlResponse {
  success: boolean;
  connectionId: string;
  sqlText: string;
  cachePath: string;
  cacheHit: boolean;
}

export interface SourceDdlRequest {
  connectionId: string;
  sqlclConnectionName: string;
  schemaName: string;
  objectType: string;
  objectName: string;
  forceRefresh?: boolean;
}

export interface SourceDdlResponse {
  success: boolean;
  connectionId: string;
  sqlText: string;
  cachePath: string;
  cacheHit: boolean;
}
