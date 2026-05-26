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
