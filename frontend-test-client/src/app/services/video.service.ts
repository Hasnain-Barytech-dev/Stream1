import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Video, StreamingManifest } from '../models/video.model';

@Injectable({
  providedIn: 'root'
})
export class VideoService {
  private apiUrl = `${environment.apiUrl}/api/v1/streams`;

  constructor(private http: HttpClient) { }

  getVideoMetadata(videoId: string): Observable<Video> {
    return this.http.get<Video>(`${this.apiUrl}/${videoId}`);
  }

  getStreamingManifest(videoId: string, format: 'hls' | 'dash' = 'hls'): Observable<StreamingManifest> {
    const params = new HttpParams().set('format', format);
    return this.http.get<StreamingManifest>(`${this.apiUrl}/${videoId}/manifest`, { params });
  }

  getThumbnail(videoId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${videoId}/thumbnail`, { responseType: 'blob' });
  }

  listMyVideos(skip: number = 0, limit: number = 20, companyId?: string, status?: string): Observable<Video[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString());
      
    if (companyId) params = params.set('company_id', companyId);
    if (status) params = params.set('status', status);
    
    return this.http.get<Video[]>(`${this.apiUrl}/my-videos`, { params });
  }

  listCompanyVideos(companyId: string, skip: number = 0, limit: number = 20, status?: string): Observable<Video[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString())
      .set('company_id', companyId);
      
    if (status) params = params.set('status', status);
    
    return this.http.get<Video[]>(`${this.apiUrl}/company-videos`, { params });
  }

  deleteVideo(videoId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${videoId}`);
  }
}