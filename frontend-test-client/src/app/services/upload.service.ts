import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpRequest, HttpEventType, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { UploadInitialization, VideoUploadProgress } from '../models/video.model';

@Injectable({
  providedIn: 'root'
})
export class UploadService {
  private apiUrl = `${environment.apiUrl}/api/v1/upload`;
  private _uploadProgress = new BehaviorSubject<{[key: string]: number}>({});
  
  uploadProgress$ = this._uploadProgress.asObservable();

  constructor(private http: HttpClient) { }

  initializeUpload(filename: string, fileSize: number, contentType: string, title?: string, description?: string): Observable<UploadInitialization> {
    return this.http.post<UploadInitialization>(`${this.apiUrl}/initialize`, {
      filename,
      file_size: fileSize,
      content_type: contentType,
      title,
      description
    });
  }

  uploadChunk(file: File, videoId: string, chunkIndex: number, totalChunks: number): Observable<VideoUploadProgress> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('video_id', videoId);
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('total_chunks', totalChunks.toString());

    const req = new HttpRequest('POST', `${this.apiUrl}/chunk`, formData, {
      reportProgress: true
    });

    return this.http.request(req).pipe(
      map((event: HttpEvent<any>) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          const progress = Math.round(100 * event.loaded / event.total);
          const currentProgress = this._uploadProgress.value || {};
          this._uploadProgress.next({
            ...currentProgress,
            [videoId]: progress
          });
        }
        
        if (event.type === HttpEventType.Response) {
          return event.body;
        }
        
        return { video_id: videoId, chunk_index: chunkIndex, total_chunks: totalChunks, progress: 0 };
      })
    );
  }

  getUploadStatus(videoId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/status/${videoId}`);
  }

  cancelUpload(videoId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${videoId}`);
  }

  // Helper method to split a file into chunks
  createChunks(file: File, chunkSize: number = 5 * 1024 * 1024): Blob[] {
    const chunks: Blob[] = [];
    let start = 0;
    
    while (start < file.size) {
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);
      chunks.push(chunk);
      start = end;
    }
    
    return chunks;
  }
}