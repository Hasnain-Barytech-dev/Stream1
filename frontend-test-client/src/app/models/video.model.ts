export interface Video {
    id: string;
    title: string;
    description?: string;
    filename: string;
    duration?: number;
    width?: number;
    height?: number;
    format: string;
    size: number;
    status: VideoStatus;
    thumbnail_url?: string;
    playback_url?: string;
    hls_url?: string;
    dash_url?: string;
    created_at: string;
    updated_at: string;
    owner_id: string;
    company_id: string;
  }
  
  export enum VideoStatus {
    PENDING = "pending",
    PROCESSING = "processing",
    READY = "ready",
    FAILED = "failed"
  }
  
  export interface VideoUploadProgress {
    video_id: string;
    chunk_index: number;
    total_chunks: number;
    progress: number;
  }
  
  export interface UploadInitialization {
    video_id: string;
    upload_url: string;
    expiration: string;
  }
  
  export interface StreamingManifest {
    video_id: string;
    manifest_url: string;
    format: 'hls' | 'dash';
    available_qualities: string[];
  }